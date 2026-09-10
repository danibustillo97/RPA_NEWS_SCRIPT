"""
media_blueprint.json -- conecta story -> scenes -> media_requirements ->
assets (docs/LAB_MEDIA_ASSETS.md). Artifact liviano: referencia por ID,
no duplica el contenido de media_plan.json ni de asset_registry.json.

Fase 4 solo necesita agregar una clave `sequence` a cada entrada de
scenes[] (asset+duration+motion+camera_motion+transition+audio+narration)
-- aditivo, no se crea vacia aca todavia (ver docs/LAB_MEDIA_INTELLIGENCE.md).
"""

import json
from typing import Any, Optional

from lab.media.paths import media_blueprint_path


def load(story_id: str) -> Optional[dict[str, Any]]:
    path = media_blueprint_path(story_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save(story_id: str, blueprint: dict[str, Any]) -> None:
    path = media_blueprint_path(story_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")


def init_blueprint(
    story_id: str,
    *,
    visual_identity: dict[str, Any],
    characters: list[str],
    references: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Crea (o reemplaza) el blueprint a partir de lo que escribió la skill
    de planning. `scenes` trae scene_id + media_requirement por escena, con
    `assets: []` todavía vacío -- generation.py los va llenando."""
    blueprint = {
        "story_id": story_id,
        "visual_identity": visual_identity,
        "characters": characters,
        "references": references,
        "scenes": [
            {"scene_id": s["scene_id"], "media_requirement": s["media_requirement"], "assets": []}
            for s in scenes
        ],
        "status": "PLANNED",
    }
    _save(story_id, blueprint)
    return blueprint


def add_asset_to_scene(story_id: str, scene_id: str, asset_id: str) -> dict[str, Any]:
    blueprint = load(story_id)
    if blueprint is None:
        raise ValueError(f"No hay media_blueprint.json para la historia {story_id!r} — correr media-init primero")
    for scene in blueprint["scenes"]:
        if scene["scene_id"] == scene_id:
            if asset_id not in scene["assets"]:
                scene["assets"].append(asset_id)
            break
    else:
        raise ValueError(f"Escena {scene_id!r} no encontrada en el blueprint de {story_id!r}")
    _save(story_id, blueprint)
    return blueprint


def set_status(story_id: str, status: str) -> dict[str, Any]:
    blueprint = load(story_id)
    if blueprint is None:
        raise ValueError(f"No hay media_blueprint.json para la historia {story_id!r}")
    blueprint["status"] = status
    _save(story_id, blueprint)
    return blueprint
