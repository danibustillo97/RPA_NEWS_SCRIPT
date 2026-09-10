"""
Sistema de jobs de LAB. Un job es "algo que Claude Code (o un humano)
le pide a la infraestructura local que haga" — hoy `run_scraper`, más
adelante `process_news`, `generate_media`, `export`, etc.

Formato de archivo: JSON, un job por archivo, en jobs/queue|done|failed/.
Ver docs/LAB_JOBS.md para el ciclo de vida completo.

Fase 1 ejecuta jobs de forma síncrona (se corren cuando se piden, acá
mismo) — no hay watcher todavía. El *formato* del job y su ciclo de vida
ya están listos para que un watcher futuro (docs/LAB_ARCHITECTURE_AUDIT.md
sección H, opción 2) simplemente lea jobs/queue/ y llame a `run_job`, sin
tener que rediseñar nada de esto.
"""

import json
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from lab.core.logging_setup import get_logger
from lab.core.paths import JOBS_DONE_DIR, JOBS_FAILED_DIR, JOBS_QUEUE_DIR, ensure_runtime_dirs

logger = get_logger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    type: str
    status: JobStatus
    params: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["status"] = self.status.value
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Job":
        d = dict(d)
        d["status"] = JobStatus(d["status"])
        return Job(**d)


# Registro de handlers — Fase 1 solo registra "run_scraper". Agregar un
# job nuevo es: escribir la función, registrarla acá. No hace falta
# tocar el resto del sistema de jobs.
_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def register_job_type(name: str):
    def decorator(fn: Callable[[dict[str, Any]], dict[str, Any]]):
        _HANDLERS[name] = fn
        return fn
    return decorator


def _job_path(job: Job, status: JobStatus) -> Path:
    dir_ = {
        JobStatus.QUEUED: JOBS_QUEUE_DIR,
        JobStatus.DONE: JOBS_DONE_DIR,
        JobStatus.FAILED: JOBS_FAILED_DIR,
    }[status if status != JobStatus.RUNNING else JobStatus.QUEUED]
    return dir_ / f"{job.id}.json"


def create_job(job_type: str, params: dict[str, Any] | None = None) -> Job:
    ensure_runtime_dirs()
    job = Job(id=uuid.uuid4().hex[:12], type=job_type, status=JobStatus.QUEUED, params=params or {})
    path = _job_path(job, JobStatus.QUEUED)
    path.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Job creado: %s (%s) -> %s", job.id, job.type, path)
    return job


def run_job(job: Job) -> Job:
    """Ejecuta un job síncronamente y mueve su archivo a done/ o failed/."""
    if job.type not in _HANDLERS:
        raise ValueError(f"Tipo de job desconocido: {job.type!r} (registrados: {list(_HANDLERS)})")

    queue_path = _job_path(job, JobStatus.QUEUED)
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc).isoformat()
    logger.info("Job %s (%s) arrancó", job.id, job.type)

    try:
        job.result = _HANDLERS[job.type](job.params)
        job.status = JobStatus.DONE
        job.finished_at = datetime.now(timezone.utc).isoformat()
        final_path = _job_path(job, JobStatus.DONE)
        logger.info("Job %s (%s) terminó OK", job.id, job.type)
    except Exception as exc:  # noqa: BLE001 — se registra el error en el job, no se oculta
        job.status = JobStatus.FAILED
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job.error = f"{exc}\n{traceback.format_exc()}"
        final_path = _job_path(job, JobStatus.FAILED)
        logger.error("Job %s (%s) falló: %s", job.id, job.type, exc)

    final_path.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    if queue_path.exists():
        queue_path.unlink()

    return job


def create_and_run(job_type: str, params: dict[str, Any] | None = None) -> Job:
    job = create_job(job_type, params)
    return run_job(job)


def record_job(
    job_type: str,
    params: dict[str, Any] | None = None,
    *,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> Job:
    """Registra un job cuyo trabajo ya lo hizo el razonamiento de Claude Code
    (no una función Python de `_HANDLERS`) — p. ej. una etapa del pipeline
    editorial de Fase 2. Usa el mismo `Job`/formato de archivo que
    `create_and_run`, directo en done/ o failed/ según si vino `error`.
    """
    ensure_runtime_dirs()
    now = datetime.now(timezone.utc).isoformat()
    job = Job(
        id=uuid.uuid4().hex[:12],
        type=job_type,
        status=JobStatus.FAILED if error else JobStatus.DONE,
        params=params or {},
        started_at=now,
        finished_at=now,
        result=result,
        error=error,
    )
    path = _job_path(job, job.status)
    path.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Job %s (%s) registrado directamente: %s", job.id, job.type, job.status.value)
    return job
