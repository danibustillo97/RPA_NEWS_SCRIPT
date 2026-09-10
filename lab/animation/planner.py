"""
animation_plan.json -- load/save/init/validate. Un solo documento vigente
por historia (mismo patron que lab.sequence.planner/lab.media.blueprint --
replanificar sobreescribe, sin versionado todavia).

init_animation_plan() hace todo el trabajo de "Animation Planner" en esta
etapa: lee sequence.json real (lab.sequence.planner.load, solo lectura) y
mapea cada SequenceShot a un AnimationShot de forma 100% deterministica --
no hay skill todavia. decide_strategy() es la unica funcion que decide
DETERMINISTIC vs AI_VIDEO, y hoy nunca produce AI_VIDEO (ver docstring de
esa funcion).
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

import lab.sequence.planner as sequence_planner
from lab.animation.constants import (
    ANIMATION_PLAN_STATUS, RENDER_BACKENDS, STRATEGY_BACKEND_MAP,
)
from lab.animation.paths import animation_plan_path
from lab.media.registry import get_asset
from lab.sequence.constants import MOTION_TYPES


def load(story_id: str) -> Optional[dict[str, Any]]:
    path = animation_plan_path(story_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save(story_id: str, plan: dict[str, Any]) -> None:
    path = animation_plan_path(story_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def decide_strategy(motion: str) -> tuple[str, str]:
    """Determinista: hoy, todo motion valido (MOTION_TYPES, definido en
    Fase 4.1) es DETERMINISTIC/FFMPEG_LOCAL -- Fase 4.1 (validate_sequence)
    ya garantiza que ningun SequenceShot.motion real puede ser otra cosa.
    Nunca devuelve AI_VIDEO en esta etapa: no hay todavia un criterio
    (humano o de skill) para decidir cuando un movimiento la necesita, y
    esa decision queda fuera de esta etapa a proposito."""
    if motion not in MOTION_TYPES:
        raise ValueError(f"motion desconocido: {motion!r} (válidos: {sorted(MOTION_TYPES)})")
    return "DETERMINISTIC", "FFMPEG_LOCAL"


def build_animation_shot(sequence_shot: dict[str, Any]) -> dict[str, Any]:
    """Transforma un SequenceShot (Fase 4.1) en un AnimationShot. Funcion
    pura, sin I/O -- no lee ni escribe ningun archivo."""
    strategy, backend = decide_strategy(sequence_shot["motion"])

    transform_required = sequence_shot.get("transform_required")
    if transform_required:
        source_transform = {
            "required": True,
            "suggested_transform": sequence_shot.get("suggested_transform"),
            "status": "PENDING",
        }
    else:
        # false o None (sin asset) -- nunca se inventa una transformacion.
        source_transform = None

    return {
        "animation_shot_id": f"anim_{sequence_shot['shot_id']}",
        "shot_id": sequence_shot["shot_id"],
        "scene_id": sequence_shot["scene_id"],
        "asset_id": sequence_shot.get("asset_id"),
        "order": sequence_shot["order"],
        "duration_seconds": sequence_shot["duration_seconds"],
        "strategy": strategy,
        "backend": backend,
        "motion": {"type": sequence_shot["motion"]},
        "transition_in": sequence_shot.get("transition_in"),
        "transition_out": sequence_shot.get("transition_out"),
        "source_transform": source_transform,
        "notes": "",
    }


def init_animation_plan(
    story_id: str, *, animation_plan_id: str = "anim_001", status: str = "DRAFT"
) -> dict[str, Any]:
    """Crea (o reemplaza) animation_plan.json a partir del sequence.json
    real de la historia -- falla si no existe (correr Fase 4.1 primero)."""
    if status not in ANIMATION_PLAN_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(ANIMATION_PLAN_STATUS)})")

    sequence = sequence_planner.load(story_id)
    if sequence is None:
        raise ValueError(f"No hay sequence.json para la historia {story_id!r} — correr Fase 4.1 primero")

    shots = [build_animation_shot(s) for s in sequence["shots"]]
    total_duration = round(sum(s["duration_seconds"] for s in shots), 3)

    plan = {
        "animation_plan_id": animation_plan_id,
        "sequence_id": sequence["sequence_id"],
        "story_id": story_id,
        "target_aspect_ratio": sequence["target_aspect_ratio"],
        "status": status,
        "shots": shots,
        "total_duration_seconds": total_duration,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(story_id, plan)
    return plan


def set_status(story_id: str, status: str) -> dict[str, Any]:
    if status not in ANIMATION_PLAN_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(ANIMATION_PLAN_STATUS)})")
    plan = load(story_id)
    if plan is None:
        raise ValueError(f"No hay animation_plan.json para la historia {story_id!r}")
    plan["status"] = status
    _save(story_id, plan)
    return plan


def validate_animation_plan(story_id: str) -> list[str]:
    """Devuelve una lista de errores (vacía si es válida). No lanza."""
    plan = load(story_id)
    if plan is None:
        return [f"No hay animation_plan.json para la historia {story_id!r}"]

    sequence = sequence_planner.load(story_id)
    if sequence is None:
        return [f"animation_plan.json existe pero no hay sequence.json para {story_id!r} (referencia rota)"]

    errors: list[str] = []

    if plan.get("story_id") != story_id:
        errors.append(f"story_id del plan ({plan.get('story_id')!r}) no coincide con {story_id!r}")
    if plan.get("sequence_id") != sequence.get("sequence_id"):
        errors.append(
            f"sequence_id del plan ({plan.get('sequence_id')!r}) no coincide con "
            f"sequence.json ({sequence.get('sequence_id')!r})"
        )
    if plan.get("target_aspect_ratio") != sequence.get("target_aspect_ratio"):
        errors.append(
            f"target_aspect_ratio del plan ({plan.get('target_aspect_ratio')!r}) no coincide con "
            f"sequence.json ({sequence.get('target_aspect_ratio')!r})"
        )

    sequence_shots_by_id = {s["shot_id"]: s for s in sequence.get("shots", [])}
    animation_shots = plan.get("shots", [])

    if not animation_shots:
        errors.append("animation_plan.json no tiene ningún shot")

    for anim_shot in animation_shots:
        aid = anim_shot.get("animation_shot_id", "<sin animation_shot_id>")
        shot_id = anim_shot.get("shot_id")
        seq_shot = sequence_shots_by_id.get(shot_id)

        if seq_shot is None:
            errors.append(f"{aid}: shot_id {shot_id!r} no existe en sequence.json de {story_id!r}")
            continue

        # Regla 1: coherencia -- no solo "existe", coincide con el original.
        for field in ("scene_id", "asset_id", "duration_seconds", "order", "transition_in", "transition_out"):
            if anim_shot.get(field) != seq_shot.get(field):
                errors.append(
                    f"{aid}: {field} ({anim_shot.get(field)!r}) no coincide con el "
                    f"SequenceShot {shot_id!r} ({seq_shot.get(field)!r})"
                )

        asset_id = anim_shot.get("asset_id")
        if asset_id is not None and get_asset(story_id, asset_id) is None:
            errors.append(f"{aid}: asset_id {asset_id!r} no existe en asset_registry.json de {story_id!r}")

        # Regla 2: strategy <-> backend.
        strategy = anim_shot.get("strategy")
        backend = anim_shot.get("backend")
        if backend not in RENDER_BACKENDS or STRATEGY_BACKEND_MAP.get(strategy) != backend:
            errors.append(
                f"{aid}: combinación strategy/backend inválida ({strategy!r}/{backend!r}) "
                f"(válidas: {STRATEGY_BACKEND_MAP})"
            )

        # Reglas 3 y 4: source_transform coherente con transform_required del SequenceShot original.
        transform_required = seq_shot.get("transform_required")
        source_transform = anim_shot.get("source_transform")
        if not transform_required:
            if source_transform is not None:
                errors.append(f"{aid}: transform_required no es true en sequence.json, source_transform debe ser null")
        else:
            if source_transform is None:
                errors.append(f"{aid}: transform_required=true en sequence.json pero source_transform es null")
            else:
                if not source_transform.get("suggested_transform"):
                    errors.append(f"{aid}: source_transform sin suggested_transform")
                if source_transform.get("status") != "PENDING":
                    errors.append(
                        f"{aid}: source_transform.status debe ser 'PENDING' en esta etapa "
                        f"(nada se ejecuta todavía), recibido {source_transform.get('status')!r}"
                    )

        # Regla 5: motion declarativo, vocabulario válido.
        motion = anim_shot.get("motion") or {}
        motion_type = motion.get("type")
        if motion_type not in MOTION_TYPES:
            errors.append(f"{aid}: motion.type {motion_type!r} inválido (válidos: {sorted(MOTION_TYPES)})")

        # Regla 6: duración positiva.
        duration = anim_shot.get("duration_seconds")
        if not isinstance(duration, (int, float)) or duration <= 0:
            errors.append(f"{aid}: duration_seconds debe ser un número positivo")

    # Regla 7: orden idéntico al de sequence.json (mismo largo, mismos valores, mismo orden de aparición).
    plan_order = [s.get("order") for s in animation_shots]
    sequence_order = [s.get("order") for s in sequence.get("shots", [])]
    if plan_order != sequence_order:
        errors.append(
            f"El orden de los shots del animation_plan ({plan_order}) no coincide "
            f"exactamente con el de sequence.json ({sequence_order})"
        )

    return errors
