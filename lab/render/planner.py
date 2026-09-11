"""
render_plan.json -- load/save/init/validate. Un solo documento vigente por
historia (mismo patron que lab.animation.planner/lab.sequence.planner --
replanificar sobreescribe, sin versionado todavia).

init_render_plan() lee animation_plan.json real (lab.animation.planner.load,
solo lectura) y mapea cada AnimationShot a un RenderShot. compute_transform_geometry()
es la unica matematica real de esta etapa -- escalado estandar (fit/cover),
nunca inventada, y solo se calcula para CROP/FIT/EXTEND (geometria pura);
COMPOSE/UNKNOWN quedan computable=false, sin numeros. Nada de esto ejecuta
FFmpeg ni ningun motor -- son los numeros que un futuro Renderer necesitaria.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

import lab.animation.planner as animation_planner
from lab.media.registry import get_asset
from lab.render.constants import (
    DEFAULT_TARGET_DIMENSIONS, GEOMETRY_COMPUTABLE_TRANSFORMS, RENDER_PLAN_STATUS,
    TARGET_DIMENSIONS,
)
from lab.render.paths import render_plan_path


def load(story_id: str) -> Optional[dict[str, Any]]:
    path = render_plan_path(story_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save(story_id: str, plan: dict[str, Any]) -> None:
    path = render_plan_path(story_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_target_dimensions(aspect_ratio: str) -> tuple[int, int]:
    """Tabla acotada de resoluciones estándar. Fuera de la tabla, cae al
    default -- mismo criterio que _dimensions_for() en cloudflare_flux.py."""
    return TARGET_DIMENSIONS.get(aspect_ratio, DEFAULT_TARGET_DIMENSIONS)


def compute_transform_geometry(
    source_width: int, source_height: int, target_width: int, target_height: int, transform_type: str
) -> dict[str, Any]:
    """Geometría de escalado estándar (fit/cover) -- nunca inventada, y
    calculada SOLO para transform_type en GEOMETRY_COMPUTABLE_TRANSFORMS.
    Para COMPOSE/UNKNOWN (no son geometría pura, son juicio editorial/IA)
    devuelve computable=false sin ningún número."""
    if transform_type not in GEOMETRY_COMPUTABLE_TRANSFORMS:
        return {"type": transform_type, "computable": False}

    if transform_type == "CROP":
        # "cover": escala para llenar ambas dimensiones, recorta el excedente.
        scale = max(target_width / source_width, target_height / source_height)
        operation = "CROP"
    else:
        # EXTEND/FIT -- "fit": escala para entrar sin exceder ninguna
        # dimensión, rellena el espacio restante (letterbox). Geométricamente
        # la misma operación para ambos en esta etapa -- ninguno implica
        # extender contenido con IA, ambos son padding.
        scale = min(target_width / source_width, target_height / source_height)
        operation = "PAD"

    scaled_width = round(source_width * scale)
    scaled_height = round(source_height * scale)

    geometry: dict[str, Any] = {
        "type": transform_type,
        "computable": True,
        "operation": operation,
        "source_width": source_width,
        "source_height": source_height,
        "scale_factor": scale,
        "scaled_width": scaled_width,
        "scaled_height": scaled_height,
    }

    diff_x = scaled_width - target_width
    diff_y = scaled_height - target_height
    if operation == "CROP":
        left = diff_x // 2
        top = diff_y // 2
        geometry.update({
            "crop_left": left, "crop_right": diff_x - left,
            "crop_top": top, "crop_bottom": diff_y - top,
        })
    else:
        pad_x = -diff_x
        pad_y = -diff_y
        left = pad_x // 2
        top = pad_y // 2
        geometry.update({
            "pad_left": left, "pad_right": pad_x - left,
            "pad_top": top, "pad_bottom": pad_y - top,
        })

    return geometry


def build_render_shot(animation_shot: dict[str, Any], story_id: str, target_width: int, target_height: int) -> dict[str, Any]:
    source_transform = animation_shot.get("source_transform")
    backend = animation_shot["backend"]

    transform_geometry = None
    if source_transform and source_transform.get("required") and backend == "FFMPEG_LOCAL":
        asset_id = animation_shot["asset_id"]
        asset = get_asset(story_id, asset_id) if asset_id else None
        if asset is not None and asset.get("width") and asset.get("height"):
            transform_geometry = compute_transform_geometry(
                asset["width"], asset["height"], target_width, target_height,
                source_transform["suggested_transform"],
            )
        else:
            # No hay dimensiones reales que leer -- no se inventa geometría.
            transform_geometry = {"type": source_transform["suggested_transform"], "computable": False}
    # backend AI_VIDEO o sin transform requerido: transform_geometry queda None
    # (un proveedor de IA resolvería el aspect ratio nativamente, no con padding).

    return {
        "render_shot_id": f"render_{animation_shot['shot_id']}",
        "animation_shot_id": animation_shot["animation_shot_id"],
        "shot_id": animation_shot["shot_id"],
        "scene_id": animation_shot["scene_id"],
        "asset_id": animation_shot["asset_id"],
        "order": animation_shot["order"],
        "duration_seconds": animation_shot["duration_seconds"],
        "strategy": animation_shot["strategy"],
        "backend": backend,
        "transform_geometry": transform_geometry,
        "status": "PENDING",
        "notes": "",
    }


def init_render_plan(
    story_id: str, *, render_plan_id: str = "render_001", status: str = "DRAFT"
) -> dict[str, Any]:
    """Crea (o reemplaza) render_plan.json a partir del animation_plan.json
    real de la historia -- falla si no existe (correr la etapa anterior primero)."""
    if status not in RENDER_PLAN_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(RENDER_PLAN_STATUS)})")

    plan_src = animation_planner.load(story_id)
    if plan_src is None:
        raise ValueError(f"No hay animation_plan.json para la historia {story_id!r} — correr la etapa anterior primero")

    target_width, target_height = compute_target_dimensions(plan_src["target_aspect_ratio"])
    shots = [build_render_shot(s, story_id, target_width, target_height) for s in plan_src["shots"]]

    plan = {
        "render_plan_id": render_plan_id,
        "animation_plan_id": plan_src["animation_plan_id"],
        "story_id": story_id,
        "target_aspect_ratio": plan_src["target_aspect_ratio"],
        "target_width": target_width,
        "target_height": target_height,
        "status": status,
        "shots": shots,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(story_id, plan)
    return plan


def set_status(story_id: str, status: str) -> dict[str, Any]:
    if status not in RENDER_PLAN_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(RENDER_PLAN_STATUS)})")
    plan = load(story_id)
    if plan is None:
        raise ValueError(f"No hay render_plan.json para la historia {story_id!r}")
    plan["status"] = status
    _save(story_id, plan)
    return plan


def validate_render_plan(story_id: str) -> list[str]:
    """Devuelve una lista de errores (vacía si es válida). No lanza."""
    plan = load(story_id)
    if plan is None:
        return [f"No hay render_plan.json para la historia {story_id!r}"]

    plan_src = animation_planner.load(story_id)
    if plan_src is None:
        return [f"render_plan.json existe pero no hay animation_plan.json para {story_id!r} (referencia rota)"]

    errors: list[str] = []

    if plan.get("story_id") != story_id:
        errors.append(f"story_id del plan ({plan.get('story_id')!r}) no coincide con {story_id!r}")
    if plan.get("animation_plan_id") != plan_src.get("animation_plan_id"):
        errors.append(
            f"animation_plan_id del plan ({plan.get('animation_plan_id')!r}) no coincide con "
            f"animation_plan.json ({plan_src.get('animation_plan_id')!r})"
        )
    if plan.get("target_aspect_ratio") != plan_src.get("target_aspect_ratio"):
        errors.append(
            f"target_aspect_ratio del plan ({plan.get('target_aspect_ratio')!r}) no coincide con "
            f"animation_plan.json ({plan_src.get('target_aspect_ratio')!r})"
        )

    src_shots_by_id = {s["animation_shot_id"]: s for s in plan_src.get("shots", [])}
    render_shots = plan.get("shots", [])

    if not render_shots:
        errors.append("render_plan.json no tiene ningún shot")

    for render_shot in render_shots:
        rid = render_shot.get("render_shot_id", "<sin render_shot_id>")
        anim_shot_id = render_shot.get("animation_shot_id")
        src_shot = src_shots_by_id.get(anim_shot_id)

        if src_shot is None:
            errors.append(f"{rid}: animation_shot_id {anim_shot_id!r} no existe en animation_plan.json de {story_id!r}")
            continue

        # Regla 1: coherencia -- coincide con el AnimationShot de origen.
        for field in ("shot_id", "scene_id", "asset_id", "order", "duration_seconds", "strategy", "backend"):
            if render_shot.get(field) != src_shot.get(field):
                errors.append(
                    f"{rid}: {field} ({render_shot.get(field)!r}) no coincide con el "
                    f"AnimationShot {anim_shot_id!r} ({src_shot.get(field)!r})"
                )

        # Reglas 3/4: transform_geometry coherente con source_transform/backend de origen.
        source_transform = src_shot.get("source_transform")
        backend = src_shot.get("backend")
        transform_geometry = render_shot.get("transform_geometry")
        needs_geometry = bool(source_transform and source_transform.get("required")) and backend == "FFMPEG_LOCAL"

        if not needs_geometry:
            if transform_geometry is not None:
                errors.append(f"{rid}: no se requiere transform_geometry (sin transform pendiente, o backend AI_VIDEO), debe ser null")
        else:
            if transform_geometry is None:
                errors.append(f"{rid}: se requiere transform_geometry (transform pendiente + backend FFMPEG_LOCAL) pero es null")
            else:
                expected_computable = source_transform["suggested_transform"] in GEOMETRY_COMPUTABLE_TRANSFORMS
                if transform_geometry.get("computable") != expected_computable:
                    errors.append(
                        f"{rid}: computable={transform_geometry.get('computable')!r} no coincide con lo esperado "
                        f"({expected_computable!r}) para suggested_transform={source_transform['suggested_transform']!r}"
                    )
                if transform_geometry.get("computable"):
                    for field in ("source_width", "source_height", "scaled_width", "scaled_height"):
                        value = transform_geometry.get(field)
                        if not isinstance(value, int) or value <= 0:
                            errors.append(f"{rid}: transform_geometry.{field} debe ser un entero positivo")
                    pad_or_crop_fields = (
                        ("pad_left", "pad_right", "pad_top", "pad_bottom") if transform_geometry.get("operation") == "PAD"
                        else ("crop_left", "crop_right", "crop_top", "crop_bottom")
                    )
                    for field in pad_or_crop_fields:
                        value = transform_geometry.get(field)
                        if not isinstance(value, int) or value < 0:
                            errors.append(f"{rid}: transform_geometry.{field} debe ser un entero ≥ 0")

        # Regla 6: status siempre PENDING en esta etapa (DONE/FAILED reservados
        # para cuando exista ejecución real -- ver RENDER_SHOT_STATUS).
        shot_status = render_shot.get("status")
        if shot_status != "PENDING":
            errors.append(f"{rid}: status debe ser 'PENDING' en esta etapa (nada se ejecuta todavía), recibido {shot_status!r}")

    # Regla 7: orden idéntico al de animation_plan.json.
    plan_order = [s.get("order") for s in render_shots]
    src_order = [s.get("order") for s in plan_src.get("shots", [])]
    if plan_order != src_order:
        errors.append(
            f"El orden de los shots del render_plan ({plan_order}) no coincide "
            f"exactamente con el de animation_plan.json ({src_order})"
        )

    return errors
