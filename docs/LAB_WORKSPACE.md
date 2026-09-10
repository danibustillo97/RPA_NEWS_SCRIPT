---
title: LAB — Workspace
status: Fase 2
date: 2026-09-10
---

# Workspace de LAB

Principio obligatorio (brief del usuario): **CÓDIGO ≠ DATOS DE TRABAJO ≠ OUTPUT ≠ LOGS**. Por eso `lab/` separa código (`core/`, `ingestion/`, `cli.py`) de datos de trabajo (`workspace/`), jobs (`jobs/`) y logs (`logs/`) en carpetas distintas — nunca mezclados.

## Carpetas de `workspace/`

| Carpeta | Estado | Quien escribe | Fase |
|---|---|---|---|
| incoming/ | INGESTED | Ingestion | 1 activa |
| processing/ | PROCESSING | Skills editoriales | 2 activa |
| review/ | READY_FOR_REVIEW | Skills editoriales | 2 activa |
| approved/ | APPROVED | El humano | 2 activa |
| rejected/ | REJECTED | El humano | 2 activa |
| media/ | sin estado propio | Media Agent | 3 |
| exports/ | EXPORTED | Export Agent | 4 |

Cada item es un archivo id.json (lab/core/workspace.py, WorkspaceItem), salvo en processing/ y review/, donde es una subcarpeta por item (id/item.json), porque ahi conviven hasta 8 artifacts editoriales mas (Fase 2, docs/LAB_ARTIFACTS.md). incoming/, approved/ y rejected/ siguen siendo archivo plano, sin cambios de Fase 1.

Moverse de un estado a otro (transition()) mueve el archivo o la carpeta completa del estado viejo al nuevo, asi el estado de un item siempre es en que carpeta esta, sin necesidad de un indice aparte. Al salir de processing/ o review/ hacia un estado de archivo plano (APPROVED/REJECTED), la subcarpeta con los artifacts no se borra, queda como archivo historico en review/id/, aunque la ubicacion canonica del item pase a ser el archivo plano.

`workspace/.dedupe_index.json` no es un item — es el índice local de URLs/slugs ya ingeridos por LAB (ver `docs/LAB_ARCHITECTURE_AUDIT.md` sección N.3, por qué es local y no Supabase).

## Regla dura: nunca se salta la revisión humana

`transition()` (en `lab/core/workspace.py`) bloquea en código, no solo en documentación, cualquier intento de pasar a `EXPORTED` sin venir de `APPROVED`:

```python
if new_state == WorkflowState.EXPORTED and item.state != WorkflowState.APPROVED:
    raise ValueError(...)
```

Probado en Fase 1 (ver informe de cierre) — intentar saltar el review lanza `ValueError`, no falla silenciosamente.

## `jobs/` y `logs/`

Ver `docs/LAB_JOBS.md` para el ciclo de vida de un job. `logs/lab-<fecha>.log` acumula todo lo que loguea cualquier módulo de LAB (vía `lab/core/logging_setup.py`), un archivo por día.

## Qué NO vive en `workspace/`

Nada de código, nada de configuración, nada de credenciales. Los archivos de `workspace/` y `jobs/` están en `.gitignore` (son datos de ejecución, no versionables) salvo los `.gitkeep` que mantienen la estructura de carpetas visible en git aunque estén vacías.
