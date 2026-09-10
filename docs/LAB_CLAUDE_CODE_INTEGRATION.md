---
title: LAB — Integración con Claude Code
status: Fase 1 (mecanismo interactivo)
date: 2026-09-10
---

# LAB → Claude Code

Ver `docs/LAB_ARCHITECTURE_AUDIT.md` sección H para las 3 opciones técnicas evaluadas. **Fase 1 implementa la opción 1 (interactivo puro)** — deliberadamente, no por limitación técnica: es la que tiene cero superficie de automatización nueva, y ya dijiste que no hace falta que el mecanismo de "despertar" esté completamente automatizado en Fase 1.

## Cómo funciona hoy

```
Usuario, en una sesión de Claude Code abierta sobre este repo
    │
    │ escribe /lab-run-scraper
    ▼
Claude Code lee .claude/commands/lab-run-scraper.md
    │
    │ ejecuta: lab/.venv/Scripts/python.exe -m lab.cli run-scraper
    ▼
lab/cli.py -> lab.core.job.create_and_run("run_scraper", params)
    │
    ▼
lab/ingestion/run.py hace el trabajo real, escribe en lab/workspace/incoming/
    │
    ▼
Claude Code reporta el resultado en texto claro
```

Comandos disponibles: `/lab-run-scraper` (con argumentos opcionales, ej. `/lab-run-scraper --max-sources 5 --max-items 5`), `/lab-status`.

## Por qué esto no cierra la puerta a la automatización futura

El comando de Claude Code es una capa finísima — 3 líneas de instrucciones que terminan llamando a `lab/cli.py`, que a su vez llama al sistema de jobs (`lab/core/job.py`). Ese sistema de jobs ya serializa cada corrida como un archivo JSON con `id/status/params/result/error` en `lab/jobs/`, exactamente el formato que un watcher necesitaría leer.

Pasar a la opción 2 (cola de archivos + watcher invocando `claude -p "..." --allowedTools ...` en modo headless) en una fase futura significa: escribir el watcher y decidir el scope de permisos con cuidado — **no** significa rediseñar `lab/core/job.py`, `lab/ingestion/`, ni el workspace. Eso ya está listo.

## Qué NO hace esta integración

No ejecuta nada sin que un humano lo pida explícitamente (ya sea tipeando el comando, o corriendo el CLI directo). No hay cron, no hay proceso en background, no hay nada escuchando en Fase 1.
