"""
Lectura/escritura de artifacts editoriales de un item — los archivos JSON
que acompañan a `item.json` dentro de su subcarpeta en PROCESSING o
READY_FOR_REVIEW (ver `lab.core.workspace.item_dir` y `_SUBFOLDER_STATES`).

Este módulo NO genera contenido editorial — solo persiste lo que produjo
el razonamiento de Claude Code al correr una skill. Cada función valida
que el nombre de artifact sea uno de los reconocidos (`ARTIFACT_NAMES`),
para no dejar basura suelta en la carpeta del item.
"""

import json
from pathlib import Path
from typing import Any, Optional

from lab.core.workspace import WorkflowState, item_dir

# Artifacts producidos por cada skill (ver docs/LAB_EDITORIAL_INTELLIGENCE.md).
# El orden importa: es el orden en que normalmente se producen dentro de
# un cluster, y el orden en que /lab-process-news corre los clusters.
STAGE_ARTIFACTS: dict[str, list[str]] = {
    "UNDERSTANDING": ["understanding.json", "research.json", "fact_check.json"],
    "STORYCRAFT": ["editorial_analysis.json", "story_concepts.json", "content_plan.json"],
    "NARRATIVE": ["hooks.json", "script.json", "scene_plan.json"],
}

ARTIFACT_NAMES: set[str] = {name for names in STAGE_ARTIFACTS.values() for name in names}

# Mínimo para que un item pueda pasar a READY_FOR_REVIEW — ver
# docs/LAB_EDITORIAL_INTELLIGENCE.md sección "cuándo un item está listo".
REQUIRED_FOR_REVIEW = ["understanding.json", "editorial_analysis.json", "content_plan.json"]


def _artifact_path(item_id: str, state: WorkflowState, filename: str) -> Path:
    if filename not in ARTIFACT_NAMES:
        raise ValueError(f"Artifact desconocido: {filename!r} (válidos: {sorted(ARTIFACT_NAMES)})")
    return item_dir(state, item_id) / filename


def write_artifact(item_id: str, state: WorkflowState, filename: str, data: dict[str, Any]) -> Path:
    path = _artifact_path(item_id, state, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_artifact(item_id: str, state: WorkflowState, filename: str) -> Optional[dict[str, Any]]:
    path = _artifact_path(item_id, state, filename)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_artifacts(item_id: str, state: WorkflowState) -> dict[str, dict[str, Any]]:
    """Todos los artifacts que ya existen para un item, indexados por nombre de archivo."""
    dir_ = item_dir(state, item_id)
    found: dict[str, dict[str, Any]] = {}
    if not dir_.exists():
        return found
    for name in ARTIFACT_NAMES:
        path = dir_ / name
        if path.exists():
            found[name] = json.loads(path.read_text(encoding="utf-8"))
    return found


def has_required_for_review(item_id: str, state: WorkflowState) -> bool:
    dir_ = item_dir(state, item_id)
    return all((dir_ / name).exists() for name in REQUIRED_FOR_REVIEW)
