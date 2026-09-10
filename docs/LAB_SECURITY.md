---
title: LAB — Seguridad
status: Fase 3
date: 2026-09-10
---

# Seguridad

## Hallazgo abierto: `.env` de producción expuesto (no es de LAB)

`RPA_NEWS_SCRIPT/.env` (raíz del repo, usado por `main.py`/`script.py`) está **trackeado en git y publicado** en GitHub, con `SUPABASE_URL`, `SUPABASE_KEY` y `OPENROUTER_API_KEY` en texto plano. Detalle completo en `docs/LAB_ARCHITECTURE_AUDIT.md` sección E.

**Estado**: sigue documentado y sin resolver — la rotación de esas credenciales es una decisión explícita del dueño del repo, no algo que LAB o esta sesión hayan tocado. LAB **no leyó, no copió, ni depende de ese `.env`** en ningún módulo (confirmable: `grep -rn "SUPABASE\|OPENROUTER" lab/` no da resultados).

Se agregó `.gitignore` en la raíz del repo (no existía) para que esto no se repita hacia adelante — no retroactivo, el `.env` ya commiteado sigue en el historial hasta que se decida purgarlo.

## Credenciales de LAB

Fase 1 (ingestión) y Fase 2 (editorial) **no usan ninguna credencial**. Fase 3 (Media Agent) sí: `GEMINI_API_KEY` y/o `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN`, según el/los provider(s) que se usen (ver `docs/LAB_MEDIA_INTELLIGENCE.md` sección Providers).

Reglas aplicadas (a los dos providers por igual):
- Las credenciales reales van en `lab/config/.env`, **nunca** hardcodeadas en un `.py`. `lab/config/settings.py :: _load_env_file()` las carga a `os.environ` en el momento de importar `settings` — parser manual mínimo (formato `KEY=VALUE`), deliberadamente sin `python-dotenv` como dependencia nueva.
- `lab/config/.env` (sin `.example`) está en `.gitignore` desde Fase 1 (patrón `*.env`/`.env`).
- Cada provider (`gemini_image.py`, `cloudflare_flux.py`) lee sus credenciales solo de `os.environ`, nunca las loguea ni las escribe en ningún artifact (`asset_registry.json`, `generation_requests.json`, jobs, logs) — confirmado por grep, ver abajo. Los mensajes de error de `cloudflare_flux.py` (401/403/etc.) son genéricos a propósito, nunca incluyen `api_token`.
- El nombre del modelo de cada provider es configurable (`GEMINI_IMAGE_MODEL`/`CLOUDFLARE_IMAGE_MODEL` en `settings.py`), nunca hardcodeado en el provider.
- `lab.media.providers.resolver` no recibe ni maneja credenciales directamente — cada provider resuelve las suyas en su propio `__init__`, así que agregar un provider nuevo no amplía la superficie de un módulo central.

**Hallazgo real durante la implementación (corregido en el momento, ocurrió DOS veces)**: tanto al pedir `GEMINI_API_KEY` como después al pedir `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN`, el usuario las pegó por error en `lab/config/.env.example` en vez de `lab/config/.env` — ese archivo **no está cubierto por `.gitignore`** (solo `.env` lo está; `.env.example` no matchea el patrón `*.env`). Ambas veces se detectó por el aviso automático de cambio de archivo, se movieron las credenciales a `lab/config/.env` de inmediato, se restauró `.env.example` a plantilla vacía, y se confirmó con `git status`/`git check-ignore` que nunca llegaron a estar staged ni commiteadas — no hubo leak real ninguna de las dos veces, pero el patrón repetido confirma que es un error fácil de cometer (los dos archivos se llaman casi igual) — cualquier sesión futura de LAB debe verificar esto explícitamente cada vez que se pida una credencial nueva, no asumir que no va a repetirse.

**Hallazgos de cuenta (no son de LAB)**:
- Gemini: con la key real, la llamada devuelve `429 RESOURCE_EXHAUSTED` (`limit: 0` en el tier gratuito) para los modelos de imagen probados — el proyecto de Google Cloud del usuario necesita billing habilitado.
- Cloudflare: con credenciales reales, `@cf/black-forest-labs/flux-2-dev` devolvió `HTTP 408` (timeout del lado de Cloudflare) en 4 intentos reales con distintos parámetros. Se descartó ese modelo (sin reintentarlo) y se corrigió el provider para el formato real de `@cf/black-forest-labs/flux-1-schnell` (JSON plano, no multipart) — con las mismas credenciales, generó una imagen real con éxito (`asset_id: img_001`, ver `docs/LAB_MEDIA_INTELLIGENCE.md`). Ningún log ni artifact de ninguna de las dos rondas expuso el token.

Detalle completo de ambos en `docs/LAB_MEDIA_INTELLIGENCE.md`. Ningún log ni mensaje de error expuso una credencial en ninguno de los dos casos.

## Scope de permisos (para cuando exista automatización, Fase 5+)

Documentado como riesgo pendiente, no resuelto porque el mecanismo automático (`LAB_ARCHITECTURE_AUDIT.md` sección H opción 2) no existe todavía: cuando se implemente, el modo headless de Claude Code (`claude -p ... --allowedTools ...`) necesita una lista explícita de herramientas permitidas, acotada a lo que LAB realmente necesita (leer/escribir en `lab/workspace`, `lab/jobs`, `lab/logs` — no acceso general al filesystem ni a producción).

## Qué se verificó

- `grep -rn "SUPABASE\|OPENROUTER\|OPENAI" lab/` → sin resultados (LAB no referencia ninguna credencial de producción).
- `grep` de `GEMINI_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` y `CLOUDFLARE_API_TOKEN` reales contra todo `RPA_NEWS_SCRIPT/` → solo aparecen en `lab/config/.env` (gitignorado); ningún log, job, artifact o doc las contiene — verificado después de los 5 intentos reales de generación con Cloudflare (4 fallidos + 1 diagnóstico).
- `git status`/`git check-ignore -v lab/config/.env` → confirmado ignorado, nunca staged (verificado después de cada uno de los dos incidentes de `.env.example`).
- `.gitignore` cubre `.env`, `lab/.venv/`, `lab/workspace/media/*/` (assets/metadata de Fase 3, igual que el resto de datos de ejecución), y los datos de ejecución de `lab/workspace`/`lab/jobs`/`lab/logs`.
