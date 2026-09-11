"""
Renderer real -- Fase 4.2 etapa 5. Primer modulo de LAB que ejecuta FFmpeg
de verdad y produce un archivo de video. Toma render_plan.json (Etapa 3,
sin cambios en su logica) y, por cada shot elegible, corre un comando de
FFmpeg standard (imagen fuente + el escalado/pad/crop YA calculado por
lab.render.planner + duracion) para producir un clip .mp4 estatico.

Alcance deliberadamente minimo (menor riesgo arquitectonico de "ejecucion
real"): un shot, una imagen ya geometricamente resuelta, sin motion/Ken-Burns,
sin concatenacion final, sin audio -- eso queda para etapas futuras (ver
docs/LAB_RENDER_ENGINE.md). Solo se procesan shots con asset_id real y
transform_geometry computable-o-null; shots sin asset (texto-only) o con
geometria no computable (COMPOSE/UNKNOWN) quedan en status "PENDING" sin
tocar -- nunca se inventa un tratamiento visual para ellos.

A diferencia de planner.py (puro, sin I/O de procesos, no modificado en esta
etapa), este modulo SI reescribe render_plan.json -- es el primer artifact
de Fase 4.2 con ejecucion real que reportar (status PENDING -> DONE/FAILED,
output_path). Hace su propia lectura/escritura de render_plan.json (mismo
formato que planner.py) en vez de agregarle una funcion de escritura a
planner.py, para mantener esa separacion clara.
"""

import json
import subprocess
from typing import Any, Optional

from lab.config import settings
from lab.core.job import register_job_type
from lab.core.logging_setup import get_logger
from lab.media.paths import story_media_dir
from lab.media.registry import get_asset
from lab.media.storage import LocalStorageProvider
from lab.render.paths import render_plan_path, rendered_video_path
from lab.render.planner import load as load_render_plan

logger = get_logger(__name__)

_FPS = 30
_FFMPEG_TIMEOUT_SECONDS = 120


def _build_filter(render_shot: dict[str, Any], target_width: int, target_height: int) -> str:
    """Funcion pura -- arma el filtro -vf de FFmpeg a partir de la geometria
    YA calculada por lab.render.planner.compute_transform_geometry(). Nunca
    recalcula ni reinterpreta esos numeros."""
    geometry = render_shot.get("transform_geometry")
    if geometry is None:
        # Sin transform requerido -- el aspect ratio ya matchea, solo hace
        # falta escalar a las dimensiones absolutas del target.
        return f"scale={target_width}:{target_height}"

    if not geometry.get("computable"):
        raise ValueError(
            f"{render_shot.get('render_shot_id')}: transform_geometry no computable "
            f"(type={geometry.get('type')!r}) -- no se puede renderizar sin inventar geometria"
        )

    scaled_width = geometry["scaled_width"]
    scaled_height = geometry["scaled_height"]
    if geometry["operation"] == "PAD":
        return (
            f"scale={scaled_width}:{scaled_height},"
            f"pad={target_width}:{target_height}:{geometry['pad_left']}:{geometry['pad_top']}:color=black"
        )
    return (
        f"scale={scaled_width}:{scaled_height},"
        f"crop={target_width}:{target_height}:{geometry['crop_left']}:{geometry['crop_top']}"
    )


def _is_eligible(render_shot: dict[str, Any]) -> bool:
    """Un shot es elegible si tiene un asset real Y (no requiere transform,
    o la transform es computable). Texto-only o COMPOSE/UNKNOWN quedan
    PENDING -- ver docstring del modulo."""
    if not render_shot.get("asset_id"):
        return False
    geometry = render_shot.get("transform_geometry")
    return geometry is None or bool(geometry.get("computable"))


def _render_one_shot(
    story_id: str, render_shot: dict[str, Any], target_width: int, target_height: int
) -> dict[str, Any]:
    """Construye y corre el comando de FFmpeg real para un shot. Nunca
    lanza -- siempre devuelve un resultado con status DONE o FAILED."""
    render_shot_id = render_shot["render_shot_id"]
    asset_id = render_shot["asset_id"]

    asset = get_asset(story_id, asset_id)
    if asset is None:
        return {"status": "FAILED", "error": f"asset {asset_id!r} no encontrado en asset_registry.json"}

    try:
        filter_arg = _build_filter(render_shot, target_width, target_height)
    except ValueError as exc:
        return {"status": "FAILED", "error": str(exc)}

    storage = LocalStorageProvider(root=story_media_dir(story_id))
    source_path = storage.url_or_path(asset["relative_path"])

    output_path = rendered_video_path(story_id, render_shot_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        settings.FFMPEG_BINARY, "-y",
        "-loop", "1", "-i", source_path,
        "-t", str(render_shot["duration_seconds"]),
        "-vf", filter_arg,
        "-r", str(_FPS),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=_FFMPEG_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return {"status": "FAILED", "error": f"FFmpeg no encontrado (binario: {settings.FFMPEG_BINARY!r})"}
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "error": f"FFmpeg excedió el timeout de {_FFMPEG_TIMEOUT_SECONDS}s"}

    if result.returncode != 0:
        return {"status": "FAILED", "error": result.stderr[-2000:]}

    if not output_path.exists() or output_path.stat().st_size == 0:
        return {"status": "FAILED", "error": "FFmpeg terminó OK pero no produjo un archivo de salida válido"}

    relative_output = f"videos/rendered/{render_shot_id}.mp4"
    logger.info("Render shot %s -> %s (%d bytes)", render_shot_id, relative_output, output_path.stat().st_size)
    return {"status": "DONE", "output_path": relative_output}


def process_render_plan(story_id: str, *, render_shot_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Procesa los shots elegibles de render_plan.json (o uno solo si se pasa
    render_shot_id). Un fallo en un shot no aborta los demas -- mismo criterio
    que lab.media.generation.process_requests. Reescribe render_plan.json con
    el status/output_path/error real de cada shot procesado."""
    plan = load_render_plan(story_id)
    if plan is None:
        raise ValueError(f"No hay render_plan.json para la historia {story_id!r} — correr /lab-render-plan primero")

    target_width = plan["target_width"]
    target_height = plan["target_height"]

    targets = [s for s in plan["shots"] if s["render_shot_id"] == render_shot_id] if render_shot_id else plan["shots"]
    if render_shot_id and not targets:
        raise ValueError(f"render_shot {render_shot_id!r} no encontrado en render_plan.json de {story_id!r}")

    results: list[dict[str, Any]] = []
    shots_by_id = {s["render_shot_id"]: s for s in plan["shots"]}

    for shot in targets:
        rid = shot["render_shot_id"]
        if not _is_eligible(shot):
            reason = "sin asset (texto-only)" if not shot.get("asset_id") else "transform_geometry no computable"
            results.append({"render_shot_id": rid, "status": "PENDING", "reason": reason})
            continue

        outcome = _render_one_shot(story_id, shot, target_width, target_height)
        shots_by_id[rid]["status"] = outcome["status"]
        shots_by_id[rid]["output_path"] = outcome.get("output_path")
        shots_by_id[rid]["error"] = outcome.get("error")
        results.append({"render_shot_id": rid, **outcome})

    render_plan_path(story_id).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def _job_handler(params: dict[str, Any]) -> dict[str, Any]:
    story_id = params["story_id"]
    render_shot_id = params.get("render_shot_id")
    results = process_render_plan(story_id, render_shot_id=render_shot_id)
    return {
        "done": sum(1 for r in results if r["status"] == "DONE"),
        "failed": sum(1 for r in results if r["status"] == "FAILED"),
        "pending": sum(1 for r in results if r["status"] == "PENDING"),
        "results": results,
    }


register_job_type("render_execute")(_job_handler)
