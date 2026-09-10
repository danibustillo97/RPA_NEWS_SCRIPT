"""
Ruta de animation_plan.json -- vive en la misma carpeta por-historia que
sequence.json/media_blueprint.json. Importa story_media_dir de
lab.media.paths (solo lectura -- ese archivo no se modifica en esta etapa).
"""

from pathlib import Path

from lab.media.paths import story_media_dir


def animation_plan_path(story_id: str) -> Path:
    return story_media_dir(story_id) / "animation_plan.json"
