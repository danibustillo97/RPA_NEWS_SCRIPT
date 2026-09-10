"""
Rutas del workspace de media -- por historia, no globales (a diferencia
de lab/core/paths.py). Se crean perezosamente al escribir, mismo patron
que item_dir() en lab/core/workspace.py.
"""

from pathlib import Path

from lab.core.paths import WORKSPACE_ROOT

MEDIA_ROOT = WORKSPACE_ROOT / "media"


def story_media_dir(story_id: str) -> Path:
    return MEDIA_ROOT / story_id


def images_dir(story_id: str, subtype: str) -> Path:
    if subtype not in ("generated", "edited", "real", "archive"):
        raise ValueError(f"Subtipo de imagen desconocido: {subtype!r}")
    return story_media_dir(story_id) / "images" / subtype


def references_dir(story_id: str) -> Path:
    return story_media_dir(story_id) / "references"


def metadata_dir(story_id: str) -> Path:
    return story_media_dir(story_id) / "metadata"


def character_profiles_dir(story_id: str) -> Path:
    return metadata_dir(story_id) / "character_profiles"


def asset_registry_path(story_id: str) -> Path:
    return metadata_dir(story_id) / "asset_registry.json"


def visual_style_path(story_id: str) -> Path:
    return metadata_dir(story_id) / "visual_style.json"


def media_plan_path(story_id: str) -> Path:
    return story_media_dir(story_id) / "media_plan.json"


def generation_requests_path(story_id: str) -> Path:
    return story_media_dir(story_id) / "generation_requests.json"


def media_blueprint_path(story_id: str) -> Path:
    return story_media_dir(story_id) / "media_blueprint.json"


def ensure_story_media_dirs(story_id: str) -> Path:
    """Crea la estructura minima para que la skill de planning pueda escribir.
    Las subcarpetas de images/ se crean bajo demanda en generation.py, no aca
    -- no tiene sentido crear images/edited/ si la historia nunca edita nada.
    """
    base = story_media_dir(story_id)
    metadata_dir(story_id).mkdir(parents=True, exist_ok=True)
    character_profiles_dir(story_id).mkdir(parents=True, exist_ok=True)
    references_dir(story_id).mkdir(parents=True, exist_ok=True)
    return base
