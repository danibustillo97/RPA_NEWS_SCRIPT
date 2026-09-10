"""
Máquina de estados del workspace de LAB (docs/LAB_ARCHITECTURE_AUDIT.md
sección J). Estado 100% local — carpetas de archivos, no una columna de
Supabase, y no tiene relación con el `status` (draft/published) que usa
producción.

    INGESTED -> PROCESSING -> READY_FOR_REVIEW -> APPROVED -> EXPORTED
                                               '-> REJECTED

Fase 1 solo produce INGESTED (la ingestión escribe acá). Las funciones
de transición a los demás estados existen para que Fase 2+ las use sin
tener que rediseñar el workspace — no se les fuerza contenido todavía.
"""

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from lab.core.paths import (
    APPROVED_DIR, INCOMING_DIR, PROCESSING_DIR, REJECTED_DIR, REVIEW_DIR,
    ensure_runtime_dirs,
)


class WorkflowState(str, Enum):
    INGESTED = "INGESTED"
    PROCESSING = "PROCESSING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPORTED = "EXPORTED"


_STATE_DIR = {
    WorkflowState.INGESTED: INCOMING_DIR,
    WorkflowState.PROCESSING: PROCESSING_DIR,
    WorkflowState.READY_FOR_REVIEW: REVIEW_DIR,
    WorkflowState.APPROVED: APPROVED_DIR,
    WorkflowState.REJECTED: REJECTED_DIR,
    # EXPORTED no tiene carpeta propia: el item sale del workspace hacia
    # workspace/exports/*.json como parte de un paquete, no como item suelto.
}

# PROCESSING y READY_FOR_REVIEW guardan el item en una subcarpeta propia
# (<id>/item.json) porque ahí conviven los artifacts editoriales de Fase 2
# (understanding.json, research.json, etc. — ver lab/editorial/artifacts.py).
# Los demás estados siguen siendo un archivo plano <id>.json, como en Fase 1.
_SUBFOLDER_STATES = {WorkflowState.PROCESSING, WorkflowState.READY_FOR_REVIEW}


def item_dir(state: WorkflowState, item_id: str) -> Path:
    """Carpeta del item para un estado con subcarpeta propia (PROCESSING/READY_FOR_REVIEW)."""
    if state not in _SUBFOLDER_STATES:
        raise ValueError(f"{state} no usa subcarpeta por item")
    return _STATE_DIR[state] / item_id


@dataclass
class WorkspaceItem:
    """Una pieza de materia prima/contenido en algún punto del flujo editorial."""
    id: str
    state: WorkflowState
    title: str
    source_url: str
    source: Optional[str] = None
    image_url: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[str] = None
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    history: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["state"] = self.state.value
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "WorkspaceItem":
        d = dict(d)
        d["state"] = WorkflowState(d["state"])
        return WorkspaceItem(**d)


def new_item_id() -> str:
    return uuid.uuid4().hex[:12]


def _path_for(state: WorkflowState, item_id: str) -> Path:
    if state not in _STATE_DIR:
        raise ValueError(f"El estado {state} no tiene carpeta propia en el workspace")
    if state in _SUBFOLDER_STATES:
        return item_dir(state, item_id) / "item.json"
    return _STATE_DIR[state] / f"{item_id}.json"


def save_item(item: WorkspaceItem) -> Path:
    ensure_runtime_dirs()
    path = _path_for(item.state, item.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_item(state: WorkflowState, item_id: str) -> WorkspaceItem:
    path = _path_for(state, item_id)
    return WorkspaceItem.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_items(state: WorkflowState) -> list[WorkspaceItem]:
    dir_ = _STATE_DIR[state]
    items = []
    if state in _SUBFOLDER_STATES:
        for sub in sorted(dir_.glob("*/item.json")):
            items.append(WorkspaceItem.from_dict(json.loads(sub.read_text(encoding="utf-8"))))
        return items
    for f in sorted(dir_.glob("*.json")):
        items.append(WorkspaceItem.from_dict(json.loads(f.read_text(encoding="utf-8"))))
    return items


def transition(item: WorkspaceItem, new_state: WorkflowState, note: str = "") -> WorkspaceItem:
    """Mueve un item de un estado a otro: borra el archivo viejo, escribe el nuevo.

    No permite saltar directo a EXPORTED salvo desde APPROVED — la regla de
    "nunca generación -> export sin revisión humana" vive acá, en código,
    no solo en el diagrama.

    Cuando el estado viejo o el nuevo usa subcarpeta por item (PROCESSING,
    READY_FOR_REVIEW — ver `_SUBFOLDER_STATES`), la carpeta completa (con
    sus artifacts editoriales) se mueve junto con el item, no solo su
    `item.json`. Si el item sale de un estado con subcarpeta hacia uno sin
    ella (p. ej. READY_FOR_REVIEW -> APPROVED/REJECTED), la subcarpeta con
    los artifacts se conserva como archivo histórico — no se borra, solo
    deja de ser la ubicación canónica del item.
    """
    if new_state == WorkflowState.EXPORTED and item.state != WorkflowState.APPROVED:
        raise ValueError(
            f"Transición inválida: solo se puede exportar desde APPROVED (item en {item.state})"
        )

    old_state = item.state
    old_dir = item_dir(old_state, item.id) if old_state in _SUBFOLDER_STATES else None
    old_path = _path_for(old_state, item.id) if old_state in _STATE_DIR else None

    item.history.append({
        "from": old_state.value,
        "to": new_state.value,
        "at": datetime.now(timezone.utc).isoformat(),
        "note": note,
    })
    item.state = new_state

    if new_state in _SUBFOLDER_STATES and old_dir is not None and old_dir.exists():
        new_dir = item_dir(new_state, item.id)
        if old_dir != new_dir:
            ensure_runtime_dirs()
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_dir), str(new_dir))
        save_item(item)
    else:
        if new_state in _STATE_DIR:
            save_item(item)
        if old_path and old_path.exists() and not (old_dir and old_state in _SUBFOLDER_STATES):
            old_path.unlink()

    return item
