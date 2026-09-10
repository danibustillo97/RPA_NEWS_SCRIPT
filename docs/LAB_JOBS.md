---
title: LAB — Jobs
status: Fase 3
date: 2026-09-10
---

# Sistema de jobs de LAB

Un job es "algo que se le pide a la infraestructura local que haga" — hoy solo `run_scraper`. El formato y ciclo de vida ya están pensados para que un mecanismo de disparo más automático (Fase 5, ver `LAB_ARCHITECTURE_AUDIT.md` sección H opción 2) pueda usarlos sin rediseño.

## Formato

Cada job es un archivo JSON, `<id>.json`, en `lab/jobs/queue|done|failed/`:

```json
{
  "id": "88e606f5c00e",
  "type": "run_scraper",
  "status": "done",
  "params": { "max_sources": 5, "max_items": 5 },
  "created_at": "2026-09-10T14:36:43Z",
  "started_at": "2026-09-10T14:36:43Z",
  "finished_at": "2026-09-10T14:37:17Z",
  "result": { "sources_visited": 5, "candidates_found": 429, "saved": 5, "skipped_duplicate": 1, "skipped_quality": 0, "errors": 0 },
  "error": null
}
```

## Ciclo de vida

```
create_job()  -> jobs/queue/<id>.json   (status: queued)
run_job()     -> status: running (en memoria)
              -> éxito: jobs/done/<id>.json   (status: done, result poblado)
              -> falla: jobs/failed/<id>.json (status: failed, error con traceback)
```

Fase 1 ejecuta jobs **síncronamente**: `create_and_run()` crea el archivo y lo corre en el mismo proceso, en la misma llamada — no hay watcher todavía. Eso es intencional (opción 1 de `LAB_ARCHITECTURE_AUDIT.md` sección H: arrancar interactivo, sin mecanismo de automatización nuevo que pueda fallar en silencio).

## `record_job()` — jobs que ya corrió el razonamiento de Claude Code (Fase 2)

Las etapas del pipeline editorial (`docs/LAB_EDITORIAL_INTELLIGENCE.md`) no las ejecuta una función Python de `_HANDLERS` — las ejecuta Claude Code razonando al correr una skill. Para esos casos, `lab.core.job.record_job(job_type, params, result=..., error=...)` escribe directo un `Job` ya en `done` (o `failed`), con el mismo formato de archivo que `create_and_run` — no es un sistema paralelo, es la misma estructura con una segunda forma de llegar a `done/`/`failed/`.

## Tipos de job registrados

| Tipo | Handler / origen | Qué hace | Fase |
|---|---|---|---|
| `run_scraper` | `lab.ingestion.run.run_scraper_job` (función Python, `_HANDLERS`) | Ingestión local completa | 1 (activa) |
| `editorial_understanding` | `record_job()`, invocado por `lab.editorial.pipeline.mark_stage_done` vía `lab.cli editorial-stage-done ... UNDERSTANDING` | Registra que la skill `lab-editorial-understanding` terminó para un item | 2 (activa) |
| `editorial_storycraft` | ídem, etapa `STORYCRAFT` | Registra que `lab-editorial-storycraft` terminó | 2 (activa) |
| `editorial_narrative` | ídem, etapa `NARRATIVE` | Registra que `lab-editorial-narrative` terminó | 2 (activa) |
| `media_plan` | `record_job()`, invocado por `lab.cli media-record-plan` | Registra que la skill `lab-media-planning` terminó de decidir el media_plan de una historia | 3 (activa) |
| `media_generation` | `_HANDLERS` (`lab.media.generation._job_handler`), vía `create_and_run()` | Ejecuta un `generation_request` con `operation: "generate"` | 3 (activa) |
| `media_edit` | ídem, `operation: "edit"` | Ejecuta un `generation_request` de edición | 3 (activa) |
| `media_retry` | ídem, reintento de un request `FAILED` | Reintenta un `generation_request` que había fallado | 3 (activa) |
| *(futuros)* `export` | — | — | 4 |

## Agregar un tipo de job nuevo

```python
from lab.core.job import register_job_type

@register_job_type("mi_job_nuevo")
def mi_handler(params: dict) -> dict:
    ...
    return {"algo": "resultado"}
```

No hace falta tocar `lab/core/job.py` ni `lab/cli.py` más que agregar el subcomando correspondiente — el registro es el único punto de conexión.
