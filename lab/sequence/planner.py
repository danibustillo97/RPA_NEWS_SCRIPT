"""
sequence.json -- load/save/validate. Un solo documento vigente por historia
(igual que media_blueprint.json/media_plan.json hoy) -- replanificar
sobreescribe, sin historial de versiones en esta primera etapa.

derive_transform_requirement() es la unica parte 100% deterministica del
modulo: compara actual_aspect_ratio (real, del asset registry) contra
target_aspect_ratio (de la secuencia) y devuelve True/False. Nunca decide
QUE transformacion hace falta -- eso es criterio de la skill
(lab-sequence-planning), validado aca solo por vocabulario y consistencia.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

from lab.media.blueprint import load as load_blueprint
from lab.media.paths import sequence_path
from lab.media.registry import get_asset
from lab.sequence.constants import MOTION_TYPES, SEQUENCE_STATUS, TRANSFORM_REQUIRED_VALUES, TRANSITION_TYPES


def load(story_id: str) -> Optional[dict[str, Any]]:
    path = sequence_path(story_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save(story_id: str, sequence: dict[str, Any]) -> None:
    path = sequence_path(story_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sequence, ensure_ascii=False, indent=2), encoding="utf-8")


def derive_transform_requirement(actual_aspect_ratio: Optional[str], target_aspect_ratio: str) -> bool:
    """True si el asset y la secuencia no comparten aspect ratio -- nunca
    decide COMO resolverlo, solo SI hace falta resolverlo. Si no hay
    actual_aspect_ratio (asset sin dimensiones conocidas), se considera que
    hace falta transformar: no se puede afirmar que coincide sin dato real."""
    if not actual_aspect_ratio:
        return True
    return actual_aspect_ratio != target_aspect_ratio


def init_sequence(
    story_id: str,
    *,
    sequence_id: str,
    target_format: str,
    target_aspect_ratio: str,
    narrative_structure: str,
    shots: list[dict[str, Any]],
    status: str = "DRAFT",
) -> dict[str, Any]:
    """Crea (o reemplaza) sequence.json. No valida contenido narrativo (eso
    lo decidió la skill) -- valida_sequence() hace la validación estructural
    antes de que esto se considere aceptado (ver lab.cli sequence-record)."""
    if status not in SEQUENCE_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(SEQUENCE_STATUS)})")

    total_duration = round(sum(s["duration_seconds"] for s in shots), 3)
    sequence = {
        "sequence_id": sequence_id,
        "story_id": story_id,
        "target_format": target_format,
        "target_aspect_ratio": target_aspect_ratio,
        "narrative_structure": narrative_structure,
        "status": status,
        "shots": shots,
        "total_duration_seconds": total_duration,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(story_id, sequence)
    return sequence


def set_status(story_id: str, status: str) -> dict[str, Any]:
    if status not in SEQUENCE_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(SEQUENCE_STATUS)})")
    sequence = load(story_id)
    if sequence is None:
        raise ValueError(f"No hay sequence.json para la historia {story_id!r}")
    sequence["status"] = status
    _save(story_id, sequence)
    return sequence


def validate_sequence(story_id: str) -> list[str]:
    """Devuelve una lista de errores (vacía si es válida). No lanza --
    lab.cli sequence-record decide qué hacer con los errores."""
    sequence = load(story_id)
    if sequence is None:
        return [f"No hay sequence.json para la historia {story_id!r}"]

    errors: list[str] = []
    blueprint = load_blueprint(story_id)
    known_scene_ids = {s["scene_id"] for s in blueprint["scenes"]} if blueprint else set()

    shots = sequence.get("shots", [])
    if not shots:
        errors.append("sequence.json no tiene ningún shot")

    seen_orders = []
    for shot in shots:
        shot_id = shot.get("shot_id", "<sin shot_id>")

        scene_id = shot.get("scene_id")
        if scene_id not in known_scene_ids:
            errors.append(f"{shot_id}: scene_id {scene_id!r} no existe en media_blueprint.json de {story_id!r}")

        asset_id = shot.get("asset_id")
        if asset_id is not None:
            if get_asset(story_id, asset_id) is None:
                errors.append(f"{shot_id}: asset_id {asset_id!r} no existe en asset_registry.json de {story_id!r}")

        motion = shot.get("motion")
        if motion not in MOTION_TYPES:
            errors.append(f"{shot_id}: motion {motion!r} inválido (válidos: {sorted(MOTION_TYPES)})")

        for field in ("transition_in", "transition_out"):
            value = shot.get(field)
            if value not in TRANSITION_TYPES:
                errors.append(f"{shot_id}: {field} {value!r} inválido (válidos: {sorted(TRANSITION_TYPES)})")

        transform_required = shot.get("transform_required")
        suggested_transform = shot.get("suggested_transform")
        if asset_id is None:
            if transform_required is not None or suggested_transform is not None:
                errors.append(f"{shot_id}: sin asset_id, transform_required/suggested_transform deben ser null")
        else:
            if transform_required is True and suggested_transform not in TRANSFORM_REQUIRED_VALUES:
                errors.append(f"{shot_id}: transform_required=true requiere suggested_transform válido (uno de {sorted(TRANSFORM_REQUIRED_VALUES)})")
            if transform_required is False and suggested_transform is not None:
                errors.append(f"{shot_id}: transform_required=false pero suggested_transform no es null")

        order = shot.get("order")
        if not isinstance(order, int):
            errors.append(f"{shot_id}: order debe ser un entero")
        else:
            seen_orders.append(order)

        duration = shot.get("duration_seconds")
        if not isinstance(duration, (int, float)) or duration <= 0:
            errors.append(f"{shot_id}: duration_seconds debe ser un número positivo")

    if seen_orders and sorted(seen_orders) != list(range(1, len(seen_orders) + 1)):
        errors.append(f"order de los shots debe ser 1..N sin huecos ni repetidos (recibido: {seen_orders})")

    return errors
