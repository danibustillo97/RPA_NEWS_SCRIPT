---
title: LAB — README
status: Fase 3 implementada
date: 2026-09-10
---

# LAB — Local Editorial & Creative Lab

Infraestructura **local** de ingestión y preparación editorial de contenido. Vive en este repo, en `lab/`, separada de `main.py`/`script.py` (que siguen siendo exclusivamente de producción). Ver `docs/LAB_ARCHITECTURE_AUDIT.md` para el razonamiento completo de arquitectura — este documento es solo "cómo lo prendo".

## Qué hace hoy

**Fase 1 — Ingestión local**: visita fuentes de noticias, extrae candidatos reales (título, url, fecha, cuerpo, imagen), aplica gates de calidad, deduplica contra su propio índice local, y guarda lo que pasa en `lab/workspace/incoming/` como items `INGESTED`.

**Fase 2 — Inteligencia Editorial**: convierte un item `INGESTED` en un paquete editorial completo (entendimiento, investigación, fact-check, ángulo, historia, formato, y — si corresponde — hooks/guion/plan de escenas), razonado por Claude Code a través de 3 skills (`.claude/skills/lab-editorial-*`), y lo deja en `READY_FOR_REVIEW` para revisión humana. Ver `docs/LAB_EDITORIAL_INTELLIGENCE.md` y `docs/LAB_ARTIFACTS.md`.

**Fase 3 — Media Intelligence**: toma una historia ya en `READY_FOR_REVIEW` (con `scene_plan.json` de Fase 2) y decide, escena por escena, qué recurso visual hace falta (`REAL_IMAGE`/`GENERATED_IMAGE`/`EDITED_IMAGE`/.../`NO_MEDIA`, con criterio, no una imagen por escena automática), razonado por Claude Code a través de una skill (`.claude/skills/lab-media-planning`), y para las que necesitan generación real, la ejecuta con el provider configurado (Gemini o Cloudflare Workers AI/FLUX.2 dev — seleccionable, sin fallback automático entre ellos) y guarda el asset con su procedencia. El `WorkspaceItem` no cambia de estado — sigue en `READY_FOR_REVIEW`. Ver `docs/LAB_MEDIA_INTELLIGENCE.md` y `docs/LAB_MEDIA_ASSETS.md`.

**No hace todavía** (fases futuras, ver `LAB_ARCHITECTURE_AUDIT.md` plan de fases): secuenciación/animación (Fase 4), ensamblaje/export a producción (Fase 5), generación real de video/audio/gráficos, ni ninguna automatización sin supervisión.

## Requisitos

- Python 3.11+ (probado con 3.13).
- Fases 1 y 2 no usan ninguna API key. Fase 3 necesita credenciales reales del provider elegido — `GEMINI_API_KEY` (con billing habilitado en el proyecto de Google Cloud/AI Studio) y/o `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN` — en `lab/config/.env` (copiar de `lab/config/.env.example`, completar ahí — **nunca** en `.env.example`, y nunca commitear `.env`). Ver `docs/LAB_MEDIA_INTELLIGENCE.md`.
- Para correr los tests: `lab/.venv/Scripts/python.exe -m pip install -r lab/requirements-dev.txt` (solo `pytest`, no se instala en runtime de producción).

## Setup (una sola vez)

```bash
cd RPA_NEWS_SCRIPT
python -m venv lab/.venv
lab/.venv/Scripts/python.exe -m pip install -r lab/requirements.txt
```

## Uso

Desde la raíz del repo:

```bash
# Correr la ingestión (todas las fuentes, tope 30 items)
lab/.venv/Scripts/python.exe -m lab.cli run-scraper

# Prueba rápida, acotada
lab/.venv/Scripts/python.exe -m lab.cli run-scraper --max-sources 5 --max-items 5

# Ver cuántos items hay en cada estado del workspace
lab/.venv/Scripts/python.exe -m lab.cli status

# Pipeline editorial completo sobre un item ya ingerido
lab/.venv/Scripts/python.exe -m lab.cli editorial-start <item_id>
lab/.venv/Scripts/python.exe -m lab.cli editorial-stage-done <item_id> UNDERSTANDING
lab/.venv/Scripts/python.exe -m lab.cli editorial-stage-done <item_id> STORYCRAFT
lab/.venv/Scripts/python.exe -m lab.cli editorial-review <item_id>

# Media (Fase 3) sobre una historia ya en READY_FOR_REVIEW
lab/.venv/Scripts/python.exe -m lab.cli media-init <story_id>
# (la skill lab-media-planning escribe media_plan.json / generation_requests.json acá)
lab/.venv/Scripts/python.exe -m lab.cli media-record-plan <story_id>
lab/.venv/Scripts/python.exe -m lab.cli media-generate <story_id>
lab/.venv/Scripts/python.exe -m lab.cli media-generate <story_id> --provider cloudflare   # override puntual
lab/.venv/Scripts/python.exe -m lab.cli media-status <story_id>

# Tests (mocks, sin gastar API real)
lab/.venv/Scripts/python.exe -m pytest lab/tests/ -v
```

O, dentro de una sesión de Claude Code abierta sobre este repo: `/lab-run-scraper`, `/lab-status`, `/lab-process-news <item_id>`, `/lab-analyze-news`, `/lab-find-stories`, `/lab-generate-hooks`, `/lab-create-script`, `/lab-media-plan <story_id>`, `/lab-generate-media <story_id>`, `/lab-media-status <story_id>` (ver `docs/LAB_CLAUDE_CODE_INTEGRATION.md`, `docs/LAB_EDITORIAL_INTELLIGENCE.md` y `docs/LAB_MEDIA_INTELLIGENCE.md`).

## Estructura

```
lab/
  cli.py                 Punto de entrada (lo que corre el humano o Claude Code)
  config/                Configuración local — sin secretos
  core/                  Sistema de jobs + estados del workspace + logging
  ingestion/             Capacidad de scraping local (ADAPT de main.py, sin Supabase)
  editorial/              Orquestación del pipeline editorial (Fase 2) — artifacts.py, pipeline.py
  media/                   Orquestación de media (Fase 3) — providers/ (gemini_image.py, cloudflare_flux.py, resolver.py), storage/, registry.py, blueprint.py, generation.py
  tests/                   Tests unitarios (pytest, mocks — ver lab/requirements-dev.txt)
  workspace/              Datos de trabajo (INGESTED, PROCESSING, ...) — no es código
  jobs/                   Cola de jobs (queue/done/failed)
  logs/                   Logs diarios
```

Ver `docs/LAB_WORKSPACE.md` para el detalle de cada carpeta y `docs/LAB_JOBS.md` para el formato de job.

## Por qué no depende de Supabase

Decisión explícita, ver `docs/LAB_ARCHITECTURE_AUDIT.md` sección N.3. LAB nunca lee ni escribe la base de datos de producción — ni siquiera para leer las noticias `draft` que ya deja `main.py`. Tiene su propia ingestión, local y bajo demanda.

## Seguridad

Ver `docs/LAB_SECURITY.md`. Resumen: Fase 1 no usa ningún secreto; el hallazgo del `.env` de producción expuesto en git sigue documentado y pendiente de que el dueño del repo rote las credenciales — LAB no lo tocó ni lo copió.
