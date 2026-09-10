---
title: LAB Architecture Audit
status: APROBADO — Fase 1 implementada (ver docs/LAB_README.md)
date: 2026-09-10
scope: RPA_NEWS_SCRIPT (este repo) + integración con cronos-news-platform (producción)
---

# Auditoría de arquitectura — LAB (Local Editorial & Creative Lab)

> Este documento es el resultado de la Fase 1 (auditoría, sin implementación) pedida antes de construir LAB. No se escribió código de LAB, no se creó la estructura de workspace, no se tocó producción. Todo lo que sigue está verificado leyendo el código real de este repo — no son suposiciones.

> [!warning] Corrección de enfoque (v2)
> La v1 de este documento diagnosticó bien el estado actual, pero razonó de forma incorrecta hacia adelante: trató el repo existente como la base a adaptar ("¿qué le falta a esto para ser LAB?"). La arquitectura objetivo (definida en la sección **N**) es la fuente de verdad, no el repo. Para cada componente la pregunta correcta es *"¿esto resuelve una necesidad real de LAB?"* — y solo entonces se reutiliza, se adapta, se deja como legacy, o se reconstruye. Las secciones A/B/C/D/E de abajo (inventario del estado actual) siguen siendo válidas tal cual — son hechos, no cambiaron. Lo que cambió es la sección **F en adelante** (la propuesta), corregida en la sección **N** y reflejada en las secciones siguientes.

## Resumen ejecutivo

Este repositorio (`RPA_NEWS_SCRIPT`) contiene **un solo pipeline realmente en producción** (`main.py`, ejecutado cada 15 minutos por GitHub Actions) y **una cantidad significativa de código huérfano** de un intento de reescritura modular que nunca se conectó — ni al workflow, ni entre sí (algunos módulos ni siquiera se pueden importar con las dependencias declaradas). Además hay un **hallazgo de seguridad urgente, independiente de LAB**: hay credenciales reales (Supabase + OpenRouter) commiteadas en `.env` y publicadas en el repo de GitHub.

Esto se parece mucho a lo que encontramos y limpiamos en `cronos-news-platform` (Content Studio): un pipeline real conviviendo con una capa "v2" abandonada. La buena noticia es que **el pipeline real es simple, autocontenido y fácil de entender** — es un excelente punto de apoyo para construir LAB encima, sin tocarlo.

---

## A. Qué existe actualmente

### A.1 — El pipeline real (lo único que corre en producción)

**`main.py`** (raíz del repo) es el **único entry point que ejecuta GitHub Actions** (`.github/workflows/scraper.yml`, cron `*/15 * * * *`, cada 15 minutos, 96 veces/día). Es un script monolítico y autocontenido (cero imports de `src/`):

1. `fetch_news()` — recorre 54 URLs hardcodeadas (`NEWS_SOURCES`, línea 67-83) de portales de noticias generales de Colombia/LatAm/España (no son solo deportivos, pese a que la app se llama "Nexus News" y su README dice "noticias deportivas" — ver hallazgo en sección C).
2. Para cada `<a href>` que matchea patrones tipo `noticia|news|/202|...`, arma un artículo candidato con título + URL + fecha (parseada con `dateparser`, de un `<time>` cercano o meta `article:published_time`).
3. `is_duplicate(slug, url)` — consulta Supabase en vivo (`news` table, `slug.eq.X,source_url.eq.Y`) antes de guardar.
4. `generate_content()` / `extract_body()` — scraping simple del HTML del artículo (meta description + párrafos `<p>`), **sin IA** — es concatenación + limpieza de texto.
5. `extract_image_url()` — primer `og:image` o `<img>` de la página; si no hay imagen real, **descarta el artículo** (no usa placeholder en prod — buena señal, evita basura visual).
6. `detect_category/league/country/team()` — heurísticas de keyword-matching contra diccionarios hardcodeados (líneas 33-65) — no es IA, es texto plano.
7. `save_article()` — inserta en Supabase `news` con `status: "draft"` (**nunca publica directo** — ya existe un estado editorial mínimo hoy).
8. Límite: máx. 30 artículos guardados por corrida, con `time.sleep(1)` entre inserciones.
9. Dedup adicional por archivo plano `visited_urls.txt` (50 URLs actualmente, commiteado a git — ver sección C).

**Contrato de datos real** (columnas que `main.py` efectivamente escribe en `news`): `title, slug, content, image_url, source_url, author, status, published_at, created_at, category, source, league, country, team, tags, summary, relevance_score, language, seo_score`. Esto es **más rico** que lo que hoy lee el frontend de `cronos-news-platform` (que solo hace `select('id, title, image_url, category, created_at, slug, content')` — ver `src/studio/engines/news/news.engine.ts` en ese repo). Hay columnas (`tags`, `summary`, `relevance_score`, `seo_score`, `league`, `country`, `team`) que ya existen en la tabla pero el frontend actual no las aprovecha.

### A.2 — Código huérfano (existe en el repo, pero no lo ejecuta nada)

Confirmado por grafo de imports real (no por inspección superficial):

| Módulo | Estado | Evidencia |
|---|---|---|
| `script.py` | Nunca automatizado (no está en ningún workflow); usa `OPENAI_API_KEY`, que **no existe** en `.env` actual (solo hay `SUPABASE_URL`, `SUPABASE_KEY`, `OPENROUTER_API_KEY`) — fallaría si se ejecutara hoy | `.github/workflows/scraper.yml` solo llama `python main.py`; `.env` no tiene `OPENAI_API_KEY` |
| `src/scraper/fetcher_news.py` | Huérfano — nada lo importa | `grep -rn "fetcher_news"` → 0 resultados fuera del propio archivo |
| `src/scraper/scrape_colombia_news_with_ai.py` | **Roto** — importa `src.scrapers.utils`, `src.scrapers.sources`, `src.supabase_client`, ninguno existe en el árbol actual (es `src/scraper` singular, `src/db/supabase.py`) | Lectura directa del archivo |
| `src/ai/rewriter.py`, `src/ai/generator.py`, `src/ai/local_ia.py` | Usan `from transformers import pipeline` (modelos `t5-small`, `t5-base`, `gpt2`, `distilbart-cnn-12-6`) — **`transformers` ni `torch` están en `requirements.txt`**, fallarían al importar | `requirements.txt`: solo `requests, beautifulsoup4, python-dotenv, supabase, dateparser, openai` |
| `src/ai/classifier.py` | Solo lo usaría `fetcher_news.py` (huérfano); depende de `src/sources_config/sources.py` | — |
| `src/sources_config/sources.py` | Solo lo importa `classifier.py` (huérfano en cadena) | `grep -rn "sources_config"` → 1 resultado |
| `src/utils/validator.py`, `media.py` | Solo los usa `fetcher_news.py` (huérfano) | — |
| `src/utils/proxy_manager.py` | Huérfano, nadie lo importa | `grep -rn "proxy_manager"` → 0 resultados |
| `src/utils/cleaner.py`, `browser.py`, `category_mapper.py` | Huérfanos, nadie los importa | `grep` → 0 resultados |
| `src/scraper/sites/zonacero_scraper.py` | Huérfano pero **bien escrito**: scraper específico por sitio con selectores CSS propios, patrón reutilizable | Import comentado en `fetcher_news.py` línea 2 |
| `src/scraper/sites/espn.py` | Archivo vacío (0 bytes), nunca implementado | — |
| `src/site_memory/zonacero.json` | Config de selectores CSS por sitio (`list_selector`, `title_selector`, etc.) — patrón interesante para "memoria" de sitio, usado únicamente por el scraper huérfano de Zona Cero | — |
| `src/db/supabase.py` | Funcional (wrapper simple de `insert`), pero solo lo usaría `fetcher_news.py` (huérfano) — `main.py`/`script.py` tienen su propia conexión inline duplicada | — |

**Conclusión de A.2**: es exactamente el mismo patrón que encontramos en `cronos-news-platform` — un intento de arquitectura modular "v2" (`src/ai`, `src/scraper` orquestado, `src/db`, `src/sources_config`, `src/utils`) que se abandonó a medio camino y quedó conviviendo con el script monolítico real, sin que nada lo conecte. Nada de este árbol corre hoy en producción.

**Sobre los "modelos de Transformers/Hugging Face débiles" que mencionás**: confirmado — `t5-small`/`t5-base` (paráfrasis), `gpt2` base (generación), `distilbart-cnn-12-6` (resumen) son modelos de 2019-2020, livianos y efectivamente débiles para nivel editorial. Pero **ni siquiera están operativos** (falta la dependencia `transformers` en `requirements.txt`, y nada los importa desde el pipeline real). No hace falta "reemplazarlos" — ya están fuera de servicio de facto. La decisión de que LAB no dependa de ellos como inteligencia editorial principal ya está tomada por el propio estado del código.

### A.3 — Duplicación de datos de dominio

`LEAGUE_KEYWORDS`, `COUNTRIES`, `TEAMS` están definidos **de forma independiente y ligeramente distinta** en 3 lugares: `main.py` (líneas 47-65), `script.py` (líneas 29-45), y `src/sources_config/sources.py`. `NEWS_SOURCES` está duplicado con distinto alcance en `main.py` (54 fuentes generales) y `script.py`/`sources_config/sources.py` (18 fuentes, solo deportivas).

---

## B/C/D. Qué conservar / desacoplar / reemplazar

**Superado por la sección N** (`Transición: de la arquitectura legacy al LAB objetivo`), que clasifica cada componente contra las necesidades reales de la arquitectura objetivo (REUSE / ADAPT-DECOUPLE / LEGACY / REBUILD / CREATE NEW), en vez de preguntar genéricamente "qué conservamos". La v1 de estas tres secciones asumía que el repo actual era la base a adaptar — la v2 invierte esa pregunta. Ver sección N para la clasificación completa y el razonamiento componente por componente.

---

## E. Riesgo de seguridad — independiente de LAB, urgente

**`.env` está trackeado en git y pusheado al repo público de GitHub** (confirmado: `git ls-files | grep env` → `.env`). Contiene `SUPABASE_URL`, `SUPABASE_KEY` (el mismo proyecto Supabase que usa `cronos-news-platform` en producción — `mxvdnf...supabase.co`) y `OPENROUTER_API_KEY` en texto plano, con historial de commits público. El propio workflow de GitHub Actions **ya usa GitHub Secrets correctamente** (`${{ secrets.SUPABASE_URL }}`, etc.) — el `.env` commiteado es redundante y es la fuga.

No hay `.gitignore` en el repo (no existe el archivo), por eso nunca se excluyó.

**Recomendación (fuera del alcance de LAB, para que decidas por separado):**
1. Rotar `SUPABASE_KEY` y `OPENROUTER_API_KEY` ya mismo (la key de Supabase es la `anon key` del mismo proyecto que usa producción — igual que en `cronos-news-platform`, se protege con RLS, pero rotarla no cuesta nada y corta cualquier uso indebido de OpenRouter).
2. `git rm --cached .env`, agregar `.gitignore` con `.env`, `__pycache__/`, `venv/`, `*.pyc`.
3. Purgar el `.env` del historial de git si te importa (BFG / `git filter-repo`) — opcional, la rotación de la key ya neutraliza el riesgo real.

No voy a tocar esto sin que me lo confirmes explícitamente — es una decisión tuya (rotar credenciales es una acción con impacto real).

---

## N. Transición: de la arquitectura legacy al LAB objetivo

### N.1 — El principio

Para cada capacidad que necesita el LAB objetivo, la pregunta no es "¿qué hay en el repo que se le parezca?" — es **"¿qué necesita realmente el dominio de LAB en este punto?"**, y recién ahí se mira si algo del repo lo resuelve.

```
CURRENT (lo que existe)              TARGET (lo que necesita LAB)
─────────────────────────           ──────────────────────────────
main.py monolítico                   Ingestión LOCAL, capacidad aislada
  scraping                             (visitar fuentes, traer materia prima)
  + dedup vía Supabase                 SIN decidir nada editorial
  + extracción de cuerpo/imagen
  + heurística de categoría/liga     Editorial Intelligence
  + inserción directa a Supabase       = Claude Code + skills, sobre la
  + status=draft                       materia prima ya ingresada

script.py (OpenAI, roto/no usado)    Media Intelligence
                                        = Media Agent + Gemini, dirigido
src/ai/* (transformers, roto)          por lo que decide Claude Code

src/scraper/* huérfano/roto          Human Review
                                        = estado local en el workspace,
src/db/supabase.py (huérfano)          NO un campo en Supabase

GitHub Actions (cron, producción)    Export
                                        = JSON al final, no al centro
                                          del diseño

                    ┌───────────────────────────┐
                    │        TRANSICIÓN          │
                    │                             │
                    │ 1. Extraer la lógica de     │
                    │    ingestión de main.py     │
                    │    (fetch + raw extract)    │
                    │    a un módulo standalone,  │
                    │    sin Supabase adentro.    │
                    │ 2. Consolidar diccionarios   │
                    │    de dominio en un solo    │
                    │    archivo de referencia.   │
                    │ 3. Dejar main.py intacto    │
                    │    para producción — no se  │
                    │    edita, se lee y se copia │
                    │    lo reutilizable.         │
                    │ 4. Todo lo demás (IA vieja, │
                    │    módulos rotos) queda     │
                    │    fuera del scope de LAB.  │
                    └───────────────────────────┘
```

**Importante**: "transición" acá no significa migrar/editar `main.py` — significa **extraer conceptualmente** la porción reutilizable (visitar una fuente, traer título/cuerpo/imagen) hacia un módulo nuevo de LAB, dejando el archivo original de producción exactamente como está. `main.py` no se toca en ningún fase de esto.

### N.2 — Clasificación completa por componente

| Componente | Clasificación | Por qué |
|---|---|---|
| `main.py :: fetch_news()` (recorrer fuentes, armar candidatos título+url+fecha) | **ADAPT** | El concepto ("visitar una fuente, extraer links candidatos") es exactamente la necesidad de ingestión de LAB. Hoy está mezclado con el resto del script — se extrae a un módulo de ingestión propio de LAB, no se reescribe desde cero. |
| `main.py :: extract_body()`, `extract_image_url()` | **ADAPT** | Capacidad real de "traer materia prima" (cuerpo, imagen) — se extrae al mismo módulo de ingestión de LAB, sin cambios de lógica. |
| `main.py :: is_duplicate()` (dedup vía query a Supabase) | **LEGACY para LAB** (se queda tal cual en `main.py`, solo para producción) | Acopla la ingestión a Supabase — exactamente el acoplamiento que la arquitectura objetivo prohíbe. LAB necesita su **propio** dedup local. |
| Dedup local — necesidad nueva | **REBUILD**, adaptando el *patrón* de `visited_urls.txt` | `visited_urls.txt` (archivo plano, sin red) ya es local-first — se reutiliza la idea, no el archivo (uno propio en el workspace de LAB, no compartido con producción). |
| `detect_category/league/country/team()` (heurística de keywords) | **LEGACY** | Es exactamente la "inteligencia editorial débil" que Claude Code reemplaza. No se adapta — se deja de usar como mecanismo de decisión. |
| `LEAGUE_KEYWORDS`, `COUNTRIES`, `TEAMS`, `CATEGORIES` (los diccionarios en sí) | **REUSE**, pero como **datos de referencia/contexto** para las skills de Claude Code — no como mecanismo de decisión | Son datos reales y curados a mano; el problema no son los datos, es que decidían solos. Como contexto que Claude Code puede consultar, siguen aportando. |
| `generate_content()` (concatenar título+cuerpo, sin IA) | **LEGACY** | Esto no es contenido editorial, es texto crudo. El workflow editorial de Claude Code hace este trabajo de verdad ahora. |
| `save_article()` (insert directo a Supabase, `status=draft`, autor hardcodeado) | **LEGACY para LAB** (se queda tal cual en `main.py`, solo para producción) | LAB no escribe a Supabase en ningún punto (ver N.3). Esta función sigue siendo la de producción, LAB no la toca ni la imita. |
| `script.py` completo (OpenAI inline) | **LEGACY** | Ni siquiera corre hoy (falta `OPENAI_API_KEY`), nunca se automatizó, y la forma (llamada única a un LLM dentro del scraper) no es el workflow editorial con revisión humana que define la arquitectura objetivo. |
| `src/ai/rewriter.py`, `generator.py`, `local_ia.py` (transformers) | **LEGACY / REMOVE LATER** | Modelos débiles, dependencias rotas (`transformers` no instalado), reemplazados por Claude Code como inteligencia editorial principal — decisión ya tomada en tu brief original. |
| `src/ai/classifier.py` | **LEGACY** | Mismo rol que `detect_category`, versión modular — mismo reemplazo. |
| `src/sources_config/sources.py` | **REUSE parcial** | Incorporar sus diccionarios al archivo único de referencia (junto con los de `main.py`/`script.py`, hoy triplicados) — no se reutiliza como módulo de clasificación. |
| `src/scraper/fetcher_news.py`, `scrape_colombia_news_with_ai.py` | **LEGACY** | Huérfanos, el segundo con imports rotos a módulos inexistentes. No hay nada operativo que rescatar; la lógica que sí vale (dedup/validación) ya está cubierta por otras filas de esta tabla. |
| `src/db/supabase.py` | **LEGACY para LAB** (nadie más lo necesita tampoco — no lo usa ni `main.py` ni `script.py`) | LAB no tiene capa de persistencia en Supabase. |
| `src/utils/validator.py` (`is_valid_article`) | **REUSE** | Gate de calidad real y simple ("¿hay título y cuerpo mínimo?") — útil tal cual como parte del módulo de ingestión de LAB. |
| `src/utils/media.py` (`is_valid_image_url`) | **REUSE** | Mismo caso — gate de calidad para imágenes, insumo directo para que el Media Agent decida "ya hay imagen real utilizable". |
| `src/utils/category_mapper.py` | **LEGACY** | Otro clasificador por keywords — mismo reemplazo que `detect_category`/`classifier.py`. |
| `src/utils/cleaner.py`, `browser.py`, `proxy_manager.py` | **LEGACY** (sin auditoría profunda de contenido — huérfanos, sin caso de uso claro hoy) | Ninguno tiene importadores; no hay necesidad actual de LAB que resuelvan. Se documentan como legacy, no se descartan del todo por si la ingestión necesita browser automation más adelante (sitios con JS pesado). |
| `src/scraper/sites/zonacero_scraper.py` + `src/site_memory/zonacero.json` | **REUSE** — patrón objetivo para ingestión futura | Scraper por sitio con selectores propios, más preciso y mantenible que el heurístico genérico de `main.py`. Es el modelo a seguir cuando LAB necesite agregar fuentes nuevas con curaduría, no el heurístico de 54 sitios genéricos. |
| `src/scraper/sites/espn.py` (vacío) | **REBUILD** si se quiere ESPN como fuente curada — no hay nada que reutilizar | Archivo vacío, nunca implementado. |
| `.github/workflows/scraper.yml` | **N/A — se queda 100% en producción** | Automatización de `main.py` en la nube; LAB dispara su propia ingestión localmente bajo demanda (sección H), no comparte este mecanismo. |
| Claude Code como operador del LAB | **CREATE NEW** | No existe hoy ningún mecanismo de jobs/comandos — ver sección H para las opciones técnicas. |
| Media Agent + integración Gemini | **CREATE NEW** | No existe absolutamente nada de generación/dirección de imágenes en el repo actual. |
| Estado de revisión humana (`INGESTED…EXPORTED`) | **CREATE NEW**, local (archivos/carpetas del workspace) | El único "estado editorial" que existe hoy es la columna `status` de Supabase, que es de **producción** (la usa el panel de News de `cronos-news-platform`) — no es ni debe ser el mismo mecanismo que el workflow interno de LAB. |
| Export JSON | **CREATE NEW**, diseñado después del modelo de dominio (no antes) | No existe ningún formato de exportación hoy. |

### N.3 — Por qué LAB queda sin dependencia de Supabase (decisión explícita)

Pediste que documentara exactamente por qué, si Supabase entra en algún punto. Respuesta corta: **no entra, y esto es una corrección respecto a la v1 de este documento**, que proponía que LAB *leyera* las noticias `draft` que `main.py` ya deja en Supabase.

Esa propuesta original violaba tu propio principio: hacía que la ingestión de LAB dependiera del cronograma y del pipeline de producción (¿qué pasa si querés ingerir algo que `main.py` todavía no scrapeó, o de una fuente que `main.py` no cubre?), y colaba a Supabase como pieza silenciosa de la arquitectura de LAB.

**Diseño corregido**: LAB invoca la capacidad de ingestión (la parte `ADAPT` de `fetch_news`/`extract_body`/`extract_image_url`, sección N.2) **directamente y localmente**, bajo demanda, escribiendo el resultado crudo directo al workspace local de LAB (`INGESTED`). Cero llamadas a Supabase en todo el ciclo de vida de LAB — ni para leer, ni para escribir, ni para dedup. La única vez que algo de LAB toca producción es en el momento del import manual del JSON exportado, y eso lo hace un humano desde `cronos-news-platform`, no LAB.

Esto también resuelve limpio tu regla de la sección 11 de tu brief original: producción sigue funcionando si LAB está apagado, y ahora además **LAB sigue funcionando si Supabase está caído** — no hay dependencia en ninguna dirección.

---

## F. Arquitectura propuesta para LAB (corregida)

```
   PRODUCCIÓN (sin cambios, sin dependencia de LAB en ningún sentido)
   ┌─────────────────────────────────────────┐
   │  RPA_NEWS_SCRIPT: main.py                 │
   │  .github/workflows/scraper.yml            │
   │  (cada 15 min) ──► Supabase news (draft)  │
   └─────────────────────────────────────────┘
              ▲ sin conexión ▼           (LAB no lee ni escribe acá)


   LAB (100% local, cero dependencia de Supabase)
   ┌─────────────────────────────────────────┐
   │  lab/  (nuevo, en este repo)              │
   │                                           │
   │  LAB UI (local)                          │
   │      │ dispara job ("RUN SCRAPER")       │
   │      ▼                                   │
   │  jobs/ (cola de archivos)                │
   │      │ Claude Code lee el job             │
   │      ▼                                   │
   │  Claude Code (operador) ── Tools/Agents  │
   │      │                                   │
   │      ├─ Ingestión LOCAL (adaptada de      │
   │      │  main.py::fetch_news/extract_*,   │
   │      │  sección N) — sin Supabase        │
   │      ├─ Research/Editorial/Story/Hook/   │
   │      │  Script (skills, ver sección G)   │
   │      ├─ Media Agent ──► Gemini ──► img   │
   │      ▼                                   │
   │  workspace/ (incoming→review→approved,   │
   │              archivos locales)            │
   │      │ human review (obligatorio)        │
   │      ▼                                   │
   │  exports/*.json  (paquete portátil)      │
   └─────────────────────────────────────────┘
                    │
                    │ IMPORT MANUAL (humano)
                    ▼
   ┌─────────────────────────────────────────┐
   │       cronos-news-platform (producción)  │
   │  News Grid → import → flujo normal       │
   │  (draft/published ya existe hoy)         │
   │  Content Studio NO lee JSON de LAB        │
   └─────────────────────────────────────────┘
```

Puntos clave que ya quedan resueltos por diseño:
- **LAB no toca Supabase en ningún punto de su ciclo de vida** — ni lee, ni escribe, ni depende de que `main.py` haya corrido antes. Su ingestión es propia, local, bajo demanda (ver N.3 para el razonamiento completo de por qué se corrigió esto respecto a la v1). El único puente con producción es el JSON exportado + import manual, exactamente como pediste en tu regla de la sección 2 ("Content Studio NO consume directamente el JSON del LAB. News recibe/importa...").
- **Producción no depende de LAB en ningún punto del runtime** — `main.py` + GitHub Actions siguen corriendo igual, apagados o no tu PC, exista o no `lab/`. Y ahora también es cierto al revés: **LAB no depende de que Supabase esté disponible**.
- El JSON de exportación es un **paquete portátil de import**, no una capa arquitectónica — un archivo, no un servicio, no una API que Content Studio consulte. Se diseña después del modelo de dominio, no antes (ver sección K).

## G. Agentes, skills, workflows y comandos — qué es cada cosa

Auditando lo que pediste (Editorial, Research, Story, Hook, Script, Fact Checker, Media, Validator, Export) contra lo que realmente hace falta para arrancar, sin sobre-ingeniería:

| Capacidad | Tipo recomendado | Por qué |
|---|---|---|
| Ejecutar la ingestión local (módulo `ADAPT` de `main.py`, **no** `main.py` en sí — ver N.2/N.3) | **Comando de Claude Code** (slash command o Bash directo) | La lógica ya existe y funciona; se extrae a un módulo propio de LAB sin Supabase, y ese módulo es lo que el comando invoca — no hace falta un "agente", solo invocarlo |
| Research (ampliar contexto de una noticia, buscar fuentes relacionadas) | **Skill** | Es una capacidad puntual que Claude Code invoca dentro de un job, no un proceso separado |
| Editorial (evaluar potencial, separar hechos de interpretación, ángulo) | **Skill / prompt estructurado**, no un "agente" con estado propio | Es razonamiento de Claude Code sobre datos ya extraídos — no necesita infraestructura propia |
| Story / Hook / Script (narrativa, guion, escenas) | **Skills encadenadas dentro de un mismo job** | Mismo razonamiento — separarlos en "agentes" distintos con IPC propio sería complejidad sin beneficio real hoy |
| Fact Checker | **Skill**, apoyada en Research | Puede necesitar acceso a web/fuentes — reutiliza la misma capacidad de research, no es un componente nuevo |
| Media Agent (dirige a Gemini) | **Sí, componente real** (no solo skill) — necesita manejar archivos, llamadas a la API de Gemini, guardar resultados en `workspace/media/` | Es la única pieza que de verdad orquesta un servicio externo con estado (imágenes generadas) |
| Validator | **Workflow / paso del job**, no agente aparte | Es una verificación de esquema antes de exportar — parte del pipeline del job, no un componente independiente |
| Export Agent | **Workflow / paso final del job** | Serializa a JSON siguiendo un esquema fijo — no necesita razonamiento propio |

**Conclusión**: para arrancar, la arquitectura real que hace falta es **un orquestador de jobs (Claude Code) + skills bien escritas + un único componente de infraestructura real (Media Agent, porque habla con Gemini y maneja archivos)**. Nueve "agentes" separados desde el día uno sería exactamente el over-engineering que pediste evitar. Se puede promover una skill a "agente" más adelante si demuestra que necesita estado/orquestación propia.

## H. LAB → Claude Code: opciones técnicas (sin decidir todavía)

Opciones reales, de menor a mayor automatismo:

1. **Interactivo puro (recomendado para arrancar)**: LAB UI es solo un panel de estado/logs; los jobs se disparan con comandos de Claude Code (`/lab-run-scraper`, `/lab-process-news`, etc.) que vos invocás en una sesión de Claude Code abierta sobre este repo. Cero mecanismo de "despertar" que construir — el operador humano ya está en el loop por definición. Más seguro, cero superficie nueva de automatización.
2. **Cola de archivos + watcher**: el botón "RUN SCRAPER" de una LAB UI local (ej. un server local mínimo) escribe un job en `lab/jobs/queue/*.json`; un proceso liviano (script Python/Node, o una Tarea Programada de Windows) vigila la carpeta y invoca `claude -p "<prompt del job>" --allowedTools ...` (modo *print*/headless del CLI de Claude Code) o usa el Claude Agent SDK para levantar una sesión programática. Esto sí logra el "LAB despierta a Claude Code" que describís, con Claude Code corriendo sin supervisión de una sesión interactiva — por eso el scope de herramientas permitidas (`--allowedTools`) y el directorio de trabajo deben quedar acotados con cuidado.
3. **Híbrido**: jobs simples (correr el scraper, exportar) vía opción 2; jobs editoriales (con juicio, ángulos, guiones) siempre disparados a mano en modo interactivo (opción 1), porque ahí el valor real es vos revisando en el momento, no automatizando.

Mi recomendación para la fase de implementación: **arrancar con la opción 1** (cero riesgo, cero mecanismo nuevo) y evolucionar a la opción 2 solo para el job de scraping (que ya es 100% determinístico y no requiere juicio editorial) una vez que el flujo manual esté probado.

## I. Claude → Gemini (Media Agent)

`Claude` no genera imágenes directamente. El Media Agent (componente real, sección G) recibe de Claude una especificación visual (qué tipo de imagen, de qué escena, con qué estilo/referencia), y decide entre 3 caminos:
- Si ya hay una imagen real utilizable (la que la ingestión local de LAB ya trajo de la fuente original, adaptado de `extract_image_url`, sección N.2) → la usa, no genera nada.
- Si hace falta una imagen nueva → llama a la API de Gemini (generación o edición a partir de referencia) y guarda el resultado en `workspace/media/<job-id>/`.
- Si la historia no necesita imagen → no genera nada (evita "imagen por generar imagen").
Todo lo que produce el Media Agent queda para revisión humana — nunca se auto-aprueba.

## J. Human Review — máquina de estados propuesta

```
INGESTED → PROCESSING → READY_FOR_REVIEW → APPROVED → EXPORTED
                                        └──► REJECTED
```
- `INGESTED`: noticia traída por la ingestión local de LAB (job "RUN SCRAPER" u otra fuente puntual) — **no** desde Supabase, ver N.3 — copiada al workspace de LAB como archivo local.
- `PROCESSING`: Claude Code está corriendo skills editoriales/narrativas sobre ella.
- `READY_FOR_REVIEW`: guion/hooks/imágenes listos, esperando que vos mires.
- `APPROVED` / `REJECTED`: tu decisión, explícita.
- `EXPORTED`: se generó el JSON portátil; de ahí en adelante es responsabilidad del import manual a `cronos-news-platform`.
Nunca hay un camino directo `PROCESSING → EXPORTED` sin pasar por `READY_FOR_REVIEW → APPROVED`.

Este estado es **enteramente local** — carpetas/archivos dentro de `workspace/` (o metadata junto a cada item), no una columna de Supabase. Es un mecanismo distinto e independiente del `status` (`draft`/`published`) que ya usa el panel de News de `cronos-news-platform` en producción — no se comparten, no se sincronizan automáticamente.

## K. Export → News

El export es un **archivo JSON versionado en `workspace/exports/`**. Su esquema se diseña **después** de tener claro el modelo de dominio de LAB (qué campos produce cada skill editorial, qué necesita el Media Agent, etc.) — no al revés — y luego se lo mapea contra las columnas reales de `news` que documentamos en A.1, para que el import a producción sea directo. Vos lo importás manualmente desde el panel de News de `cronos-news-platform` (o un pequeño script de import que corra ahí, fuera de LAB). LAB no llama a la API de producción ni inserta en Supabase de producción directamente — el JSON es la única superficie de contacto entre los dos sistemas.

## L. Mantener LAB fuera de Vercel

Dado que `RPA_NEWS_SCRIPT` es un repo Python **separado** de `cronos-news-platform` (el que sí se despliega a Vercel), y dado que LAB va a apoyarse en las capacidades de este repo (scraper) más una capa nueva, la estrategia más simple y segura es:

**LAB vive físicamente en este repo (`RPA_NEWS_SCRIPT`) en una carpeta `lab/` nueva, no dentro de `cronos-news-platform`.** Este repo nunca se construye ni se despliega en Vercel (no es un proyecto Next.js, no tiene `vercel.json` ni está conectado a Vercel) — cero riesgo de que LAB termine expuesto públicamente, sin necesidad de configurar root directories, monorepo, ni exclusiones de build. Es la opción de menor complejidad que ya cumple la regla de aislamiento por construcción, no por configuración.

Si en el futuro hiciera falta que LAB y `cronos-news-platform` compartan código (tipos del esquema `news`, por ejemplo), se evalúa en ese momento — no conviene decidir monorepo ahora "por si acaso".

## M. Documentación y Vault

Encontré el Vault existente: `C:\Users\User\Desktop\news\obsidian-vault\` (Obsidian, dentro de `cronos-news-platform`), con notas sobre arquitectura, ramas, Supabase, stack técnico. Lo respeto y lo uso como referencia de convención (frontmatter simple, wikilinks, notas cortas y concretas).

Propuesta de documentación para LAB (en este repo, `RPA_NEWS_SCRIPT/docs/`, siguiendo el mismo estilo):
- `docs/LAB_ARCHITECTURE_AUDIT.md` — este documento.
- `docs/LAB_README.md` — qué es LAB, cómo se prende, requisitos locales.
- `docs/LAB_FLOW.md` — el diagrama de flujo de la sección F, explicado paso a paso.
- `docs/LAB_AGENTS.md` — tabla de la sección G, actualizada a medida que se implementa.
- `docs/LAB_JOBS.md` — formato de job, ciclo de vida, cómo se agregan nuevos tipos de job.
- `docs/LAB_CLAUDE_CODE_INTEGRATION.md` — el mecanismo elegido en la sección H, con instrucciones reales de uso.
- `docs/LAB_GEMINI_INTEGRATION.md` — cómo se llama a Gemini, qué credenciales hacen falta, límites.
- `docs/LAB_WORKSPACE.md` — estructura de carpetas del workspace, una vez definida.
- `docs/LAB_EXPORT_FORMAT.md` — esquema del JSON de exportación, mapeado a las columnas de `news`.
- `docs/LAB_SECURITY.md` — manejo de credenciales locales (Gemini, Supabase), scope de permisos de Claude Code en modo no interactivo.

Además, voy a agregar **una nota corta en el Vault de `cronos-news-platform`** (`obsidian-vault/`) que apunte a este repo y a esta auditoría, sin duplicar contenido — solo un puente, seas por dónde entres a buscar contexto.

---

## Plan de implementación por fases (propuesto, no ejecutado)

**Fase 0 (aparte, tu decisión):** rotar credenciales expuestas, agregar `.gitignore`, sacar `.env` del tracking de git.

**Fase 1:** crear `lab/` en este repo con la estructura de workspace mínima (a definir juntos, no antes de tu aprobación de este documento) y un módulo de ingestión propio de LAB — **extraído** (no invocado) de las partes `ADAPT` de `main.py` (`fetch_news`, `extract_body`, `extract_image_url`, sección N.2), sin ninguna llamada a Supabase, con dedup local propio. Un comando de Claude Code dispara esa ingestión y deja el resultado en el workspace (`INGESTED`). Importante: **no se ejecuta `main.py` desde LAB** — ese script sigue siendo exclusivamente de producción (inserta directo a la Supabase real). Sin IA editorial todavía — solo el puente ingestión → workspace.

**Fase 2:** skills editoriales (Research/Editorial/Story/Hook/Script) operando sobre lo que está en `INGESTED`, moviendo a `PROCESSING` → `READY_FOR_REVIEW`. Sin Media Agent todavía.

**Fase 3:** Media Agent + integración con Gemini, con revisión humana de imágenes.

**Fase 4:** Export Agent (JSON) + documentación del formato + prueba de import manual a `cronos-news-platform`.

**Fase 5 (opcional):** cola de jobs + watcher para automatizar el disparo del scraper (sección H, opción 2) — solo después de que las fases 1-4 estén probadas a mano.

---

## Riesgos identificados (resumen)

1. **Credenciales expuestas en `.env` commiteado** (sección E) — urgente, independiente de LAB.
2. Falta de `.gitignore` — permite que vuelva a pasar.
3. `script.py` y todo `src/` están rotos o desconectados — no confiar en ellos sin arreglarlos explícitamente primero.
4. Desalineamiento fuente-vs-producto (scraper generalista vs. plataforma deportiva) — decisión editorial pendiente.
5. Dedup: producción sigue usando sus dos mecanismos (`visited_urls.txt` + query a Supabase), sin cambios. LAB necesita su **propio** dedup local, separado (sección N.3) — si no se separa bien, riesgo de reprocesar o de creer erróneamente que algo "ya existe" cruzando estados que no deberían cruzarse.
6. Modo headless de Claude Code (sección H, opción 2) necesita scope de permisos cuidadosamente acotado antes de automatizarse — no es un riesgo hoy porque no existe todavía.

---

## ESPERANDO APROBACIÓN PARA IMPLEMENTAR

No se ha creado la carpeta `lab/`, ni el workspace, ni ningún agente, skill o comando. Esta v2 corrige el error de enfoque de la v1 (dejar de tratar el repo actual como la base a adaptar, y en particular sacar a Supabase del camino crítico de LAB — sección N.3). La clasificación componente por componente está en la sección N.2. Decime qué ajustar, o confirmá esta arquitectura TARGET para arrancar la Fase 1.
