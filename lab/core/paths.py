"""
Rutas centrales de LAB. Un solo lugar de verdad para dónde vive cada cosa,
para que ningún módulo tenga que adivinar/reconstruir paths.

CÓDIGO (lab/*.py, lab/core, lab/ingestion) != DATOS DE TRABAJO (workspace/)
!= JOBS (jobs/) != LOGS (logs/) — carpetas separadas a propósito, ver
docs/LAB_WORKSPACE.md.
"""

from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent.parent

WORKSPACE_ROOT = LAB_ROOT / "workspace"
INCOMING_DIR = WORKSPACE_ROOT / "incoming"        # INGESTED
PROCESSING_DIR = WORKSPACE_ROOT / "processing"    # PROCESSING (Fase 2+)
REVIEW_DIR = WORKSPACE_ROOT / "review"            # READY_FOR_REVIEW (Fase 2+)
APPROVED_DIR = WORKSPACE_ROOT / "approved"        # APPROVED (Fase 2+)
REJECTED_DIR = WORKSPACE_ROOT / "rejected"        # REJECTED (Fase 2+)
MEDIA_DIR = WORKSPACE_ROOT / "media"              # media generada/editada (Fase 3+)
EXPORTS_DIR = WORKSPACE_ROOT / "exports"          # paquetes JSON exportados (Fase 4+)

DEDUPE_INDEX_FILE = WORKSPACE_ROOT / ".dedupe_index.json"

JOBS_ROOT = LAB_ROOT / "jobs"
JOBS_QUEUE_DIR = JOBS_ROOT / "queue"
JOBS_DONE_DIR = JOBS_ROOT / "done"
JOBS_FAILED_DIR = JOBS_ROOT / "failed"

LOGS_DIR = LAB_ROOT / "logs"

ALL_RUNTIME_DIRS = [
    INCOMING_DIR, PROCESSING_DIR, REVIEW_DIR, APPROVED_DIR, REJECTED_DIR,
    MEDIA_DIR, EXPORTS_DIR,
    JOBS_QUEUE_DIR, JOBS_DONE_DIR, JOBS_FAILED_DIR,
    LOGS_DIR,
]


def ensure_runtime_dirs() -> None:
    """Crea las carpetas de datos de trabajo si no existen. Idempotente."""
    for d in ALL_RUNTIME_DIRS:
        d.mkdir(parents=True, exist_ok=True)
