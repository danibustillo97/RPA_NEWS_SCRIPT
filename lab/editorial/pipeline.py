"""
Orquestación del pipeline editorial de Fase 2: mover un item por
INGESTED -> PROCESSING -> READY_FOR_REVIEW, registrando cada etapa
(cluster de skill) en `item.history` y como job trazable en `lab/jobs/`.

Quién hace el trabajo real (entender la noticia, investigar, verificar,
encontrar el ángulo) es el razonamiento de Claude Code corriendo una skill
en `.claude/skills/lab-editorial-*` — este módulo solo registra lo que
esa skill ya escribió como artifacts (ver `lab.editorial.artifacts`).
"""

from datetime import datetime, timezone

from lab.core.job import record_job
from lab.core.logging_setup import get_logger
from lab.core.workspace import (
    WorkflowState,
    WorkspaceItem,
    item_dir,
    load_item,
    save_item,
    transition,
)
from lab.editorial.artifacts import STAGE_ARTIFACTS, has_required_for_review

logger = get_logger(__name__)

STAGES = list(STAGE_ARTIFACTS.keys())  # ["UNDERSTANDING", "STORYCRAFT", "NARRATIVE"]


def start_processing(item_id: str, note: str = "") -> WorkspaceItem:
    """INGESTED -> PROCESSING. Falla si el item no está en INGESTED."""
    item = load_item(WorkflowState.INGESTED, item_id)
    return transition(item, WorkflowState.PROCESSING, note=note or "Arranca pipeline editorial")


def mark_stage_done(item: WorkspaceItem, stage: str, note: str = "") -> WorkspaceItem:
    """Registra que un cluster de skill (UNDERSTANDING/STORYCRAFT/NARRATIVE)
    terminó para este item: exige que al menos uno de sus artifacts ya
    haya sido escrito (con `lab.editorial.artifacts.write_artifact`),
    anota la etapa en `item.history`, y deja un job trazable en
    `lab/jobs/done/`.
    """
    if stage not in STAGE_ARTIFACTS:
        raise ValueError(f"Etapa desconocida: {stage!r} (válidas: {STAGES})")
    if item.state not in (WorkflowState.PROCESSING, WorkflowState.READY_FOR_REVIEW):
        raise ValueError(
            f"El item {item.id} está en {item.state}, no en PROCESSING/READY_FOR_REVIEW — "
            "corré start_processing() primero"
        )

    dir_ = item_dir(item.state, item.id)
    artifacts_present = [f for f in STAGE_ARTIFACTS[stage] if (dir_ / f).exists()]
    if not artifacts_present:
        raise ValueError(
            f"No hay artifacts escritos para la etapa {stage} del item {item.id} — "
            f"escribilos con lab.editorial.artifacts.write_artifact() antes de marcar la etapa"
        )

    item.history.append({
        "stage": stage,
        "artifacts": artifacts_present,
        "at": datetime.now(timezone.utc).isoformat(),
        "note": note,
    })
    save_item(item)

    record_job(
        f"editorial_{stage.lower()}",
        params={"item_id": item.id},
        result={"artifacts": artifacts_present},
    )
    logger.info("Item %s: etapa %s registrada (%s)", item.id, stage, ", ".join(artifacts_present))
    return item


def can_move_to_review(item_id: str) -> bool:
    return has_required_for_review(item_id, WorkflowState.PROCESSING)


def move_to_review(item: WorkspaceItem, note: str = "") -> WorkspaceItem:
    """PROCESSING -> READY_FOR_REVIEW. Exige el mínimo de artifacts
    (`lab.editorial.artifacts.REQUIRED_FOR_REVIEW`) — si `storycraft`
    concluyó que no hay ángulo/historia, igual deben existir
    understanding + editorial_analysis + content_plan (este último
    explicando por qué no se generó nada narrativo).
    """
    if item.state != WorkflowState.PROCESSING:
        raise ValueError(f"El item {item.id} está en {item.state}, no en PROCESSING")
    if not can_move_to_review(item.id):
        raise ValueError(
            f"El item {item.id} no tiene los artifacts mínimos "
            "(understanding.json, editorial_analysis.json, content_plan.json) "
            "para pasar a READY_FOR_REVIEW"
        )
    return transition(item, WorkflowState.READY_FOR_REVIEW, note=note or "Pipeline editorial completo")
