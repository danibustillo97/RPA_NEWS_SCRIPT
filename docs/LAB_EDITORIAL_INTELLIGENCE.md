---
title: LAB — Inteligencia Editorial (Fase 2)
status: Fase 2 implementada
date: 2026-09-10
---

# Inteligencia Editorial

Fase 2 convierte un item `INGESTED` (noticia cruda, ver `docs/LAB_ARCHITECTURE_AUDIT.md`) en un paquete editorial completo, sin publicar nada y sin saltarse nunca la revisión humana (`docs/LAB_WORKSPACE.md`). A diferencia de la ingestión (Fase 1, código determinístico), acá el trabajo real lo hace el **razonamiento de Claude Code** al correr una skill — el código Python de `lab/editorial/` solo orquesta: mueve el item entre estados, guarda los artifacts que la skill produjo, registra el job.

## Las 3 skills (clusters, no 9 agentes)

Las 9 capacidades del pipeline se agrupan en 3 skills — cada una corresponde a una pausa natural, no hay 9 procesos independientes coordinándose entre sí:

| Skill | Produce | Depende de |
|---|---|---|
| `lab-editorial-understanding` | `understanding.json`, `research.json`, `fact_check.json` | — (arranca del `item.json` crudo) |
| `lab-editorial-storycraft` | `editorial_analysis.json`, `story_concepts.json`, `content_plan.json` | `understanding.json` |
| `lab-editorial-narrative` | `hooks.json`, `script.json`, `scene_plan.json` | `content_plan.json` con `narrative_recommended: true` |

Esquema completo de cada artifact y la taxonomía NO INVENTAR (`SOURCE_FACT`/`VERIFIED_CONTEXT`/`INFERENCE`/`CREATIVE_FRAMING`/`UNVERIFIED`): `docs/LAB_ARTIFACTS.md`.

## Flujo end-to-end

```
INGESTED (lab/workspace/incoming/<id>.json)
   |  lab.cli editorial-start <id>
   v
PROCESSING (lab/workspace/processing/<id>/item.json)
   |  skill lab-editorial-understanding escribe understanding/research/fact_check.json
   |  lab.cli editorial-stage-done <id> UNDERSTANDING
   |  skill lab-editorial-storycraft escribe editorial_analysis/story_concepts/content_plan.json
   |  lab.cli editorial-stage-done <id> STORYCRAFT
   |  [si content_plan.json.narrative_recommended:
   |     skill lab-editorial-narrative escribe hooks/script/scene_plan.json
   |     lab.cli editorial-stage-done <id> NARRATIVE]
   |  lab.cli editorial-review <id>
   v
READY_FOR_REVIEW (lab/workspace/review/<id>/, item.json + todos los artifacts)
   |  humano revisa (fuera de LAB, a mano)
   v
APPROVED / REJECTED   (sin cambios respecto a Fase 1 -- 100% manual)
```

`lab.cli editorial-review` exige como mínimo `understanding.json` + `editorial_analysis.json` + `content_plan.json` (ver `lab.editorial.artifacts.REQUIRED_FOR_REVIEW`) — si `storycraft` decidió que no hay ángulo, el item igual llega a revisión, con `content_plan.json` explicando por qué no se generó nada narrativo.

## "No hay historia" es una salida válida

`lab-editorial-storycraft` puede — y debe, cuando corresponde — concluir `story_concepts.json :: has_story: false` con `reason_if_not` explicando el motivo, y `content_plan.json :: narrative_recommended: false`. Esto **no es un error ni un fallo del pipeline**: es el comportamiento correcto para una noticia puramente informativa (precios, horarios, decretos) que no tiene ángulo humano/narrativo. Forzar un hook o un guion sobre una noticia sin historia sería peor que no generarlo — la skill `lab-editorial-narrative` simplemente no corre en ese caso.

## Investigación (`research.json`) y búsqueda web

`lab-editorial-understanding` puede usar la herramienta de búsqueda web (`WebSearch`/`WebFetch`) ya disponible en Claude Code para resolver un `context_need`, con dos reglas estrictas:

1. **Citación obligatoria**: toda respuesta que use búsqueda web lleva su `source_url` propio en `research.json`. Nunca se mezcla con `understanding.json` (que es solo lo que dice la fuente original).
2. **`NEEDS_RESEARCH` es un resultado aceptable**: si la búsqueda no encuentra una fuente confiable, el `context_need` queda en `status: NEEDS_RESEARCH` — no se completa con una inferencia disfrazada de hecho verificado.

Se optó por habilitar la búsqueda real (en vez de dejar la skill sin buscar nada afuera) porque, sin ella, `research.json` iba a estar dominado casi siempre por `NEEDS_RESEARCH` incluso en casos donde una fuente pública ya resuelve la pregunta — era el punto abierto marcado en el plan de Fase 2, resuelto con la opción recomendada ahí.

## Qué NO hace Fase 2 (alcance)

- No genera ni edita imágenes/video (`scene_plan.json` solo **decide** qué tipo de media hace falta — `REAL_IMAGE`/`GENERATED_IMAGE`/`EDITED_IMAGE`/`NO_IMAGE` — la generación real es el Media Agent, Fase 3).
- No exporta ni publica nada — el máximo estado que produce es `READY_FOR_REVIEW`.
- No toca Supabase ni producción, igual que Fase 1.
- No procesa items en lote sin supervisión — cada corrida de `/lab-process-news` es una interacción real de Claude Code razonando sobre un item a la vez.

## Comandos de Claude Code

Ver `.claude/commands/lab-process-news.md`, `lab-analyze-news.md`, `lab-find-stories.md`, `lab-generate-hooks.md`, `lab-create-script.md`. Todos terminan, como mucho, en `READY_FOR_REVIEW` — ninguno aprueba, exporta ni publica.

## CLI (lo que usan las skills para la parte de estado/bookkeeping)

```
lab/.venv/Scripts/python.exe -m lab.cli editorial-start <item_id>          # INGESTED -> PROCESSING
lab/.venv/Scripts/python.exe -m lab.cli editorial-stage-done <item_id> UNDERSTANDING|STORYCRAFT|NARRATIVE
lab/.venv/Scripts/python.exe -m lab.cli editorial-review <item_id>         # PROCESSING -> READY_FOR_REVIEW
lab/.venv/Scripts/python.exe -m lab.cli editorial-show <item_id>           # item + artifacts, en PROCESSING o READY_FOR_REVIEW
```

Las skills escriben los archivos de artifact directamente con el tool `Write` (path determinístico: `lab/workspace/processing/<item_id>/<artifact>.json`, o `lab/workspace/review/<item_id>/` una vez que pasó a revisión) — el CLI no genera contenido, solo valida y registra.
