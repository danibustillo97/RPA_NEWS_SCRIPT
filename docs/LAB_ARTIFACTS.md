---
title: LAB — Artifacts editoriales
status: Fase 2
date: 2026-09-10
---

# Artifacts editoriales

Cada item que entra al pipeline de inteligencia editorial (Fase 2, ver `docs/LAB_EDITORIAL_INTELLIGENCE.md`) acumula estos archivos JSON en su propia carpeta (`lab/workspace/processing/<item_id>/` mientras se procesa, `lab/workspace/review/<item_id>/` al llegar a `READY_FOR_REVIEW`) junto a `item.json`. Los escriben las skills `.claude/skills/lab-editorial-*` con el tool `Write`, directo al path del item — no hay una capa Python que genere este contenido.

Todos comparten `item_id` (el id del `WorkspaceItem`) como primer campo, para que cada archivo sea auto-identificable si se abre suelto.

## Taxonomía NO INVENTAR (provenance)

Todo hecho, dato o afirmación que aparece en cualquier artifact debe llevar una etiqueta de procedencia. Nunca se presenta algo como hecho si no lo es:

| Valor | Significa |
|---|---|
| `SOURCE_FACT` | Viene literal de la noticia fuente (`item.content`) |
| `VERIFIED_CONTEXT` | Contexto externo confirmado con una fuente citada (`source_url` propio) |
| `INFERENCE` | Conclusión razonada a partir de lo anterior, no un hecho nuevo |
| `CREATIVE_FRAMING` | Elección narrativa/editorial (un hook, un ángulo) — no es un hecho, es una decisión de formato |
| `UNVERIFIED` | No se pudo confirmar; se declara explícitamente en vez de inventarse |

## `understanding.json`

```json
{
  "item_id": "793ff158b714",
  "headline": "...",
  "what_happened": "...",
  "who": ["..."],
  "what": "...",
  "when": "...",
  "where": "...",
  "why": "...",
  "how": "...",
  "key_facts": [
    {"fact": "...", "provenance": "SOURCE_FACT"}
  ],
  "entities": ["..."],
  "important_numbers": [{"value": "23 años", "context": "edad de la persona"}],
  "source": "...",
  "source_url": "...",
  "source_date": "2026-09-10",
  "uncertainty": ["..."],
  "missing_information": ["..."]
}
```

`missing_information` y `uncertainty` son campos de primera clase, no un detalle opcional — declarar explícitamente lo que la noticia fuente no dice es tan importante como registrar lo que sí dice.

## `research.json`

```json
{
  "item_id": "793ff158b714",
  "context_needs": [
    {
      "question": "...",
      "why_it_matters": "...",
      "status": "NEEDS_RESEARCH",
      "answer": null,
      "source_url": null
    }
  ],
  "related_questions": ["..."]
}
```

`status` es `NEEDS_RESEARCH` (no se pudo o no se buscó) o `VERIFIED_CONTEXT` (se encontró y confirmó — en ese caso `answer` y `source_url` van llenos). Ver la nota sobre búsqueda web en `docs/LAB_EDITORIAL_INTELLIGENCE.md`.

## `fact_check.json`

```json
{
  "item_id": "793ff158b714",
  "claims": [
    {"claim": "...", "classification": "SOURCE_ONLY", "basis": "..."}
  ]
}
```

`classification`: `VERIFIED` (confirmado con fuente propia) | `SOURCE_ONLY` (solo lo dice la fuente original, no se verificó independientemente) | `UNVERIFIED` (no se pudo evaluar) | `CONTRADICTED` (otra fuente lo contradice) | `NEEDS_RESEARCH`.

## `editorial_analysis.json`

```json
{
  "item_id": "793ff158b714",
  "why_it_matters": "...",
  "angle": "HUMAN_ANGLE",
  "narrative_strength": "HIGH",
  "reasoning": "...",
  "provenance": "INFERENCE"
}
```

`angle`: `NEWS_ANGLE` | `STORY_ANGLE` | `HUMAN_ANGLE` | `HISTORICAL_ANGLE` | `EXPLAINER_ANGLE` | `CONTROVERSY_ANGLE` | `UNKNOWN_FACT_ANGLE` | `DOCUMENTARY_ANGLE` | `NONE` (sin ángulo claro — resultado válido). `narrative_strength`: `HIGH` | `MEDIUM` | `LOW` | `NONE`.

## `story_concepts.json`

```json
{
  "item_id": "793ff158b714",
  "has_story": true,
  "reason_if_not": null,
  "concepts": [
    {"title": "...", "summary": "...", "angle": "HUMAN_ANGLE", "provenance": "CREATIVE_FRAMING"}
  ]
}
```

Cuando `has_story` es `false`, `concepts` queda vacío y `reason_if_not` explica por qué ("NO HAY HISTORIA SUFICIENTEMENTE FUERTE" es una salida válida, no un fallo — ver `docs/LAB_EDITORIAL_INTELLIGENCE.md`).

## `content_plan.json`

```json
{
  "item_id": "793ff158b714",
  "recommended_formats": [{"format": "REEL", "reason": "..."}],
  "narrative_recommended": true,
  "reason": "..."
}
```

`format`: `NEWS` | `EXPLAINER` | `REEL` | `STORY` | `CAROUSEL` | `NONE`. `narrative_recommended` decide si `/lab-process-news` sigue a la skill `lab-editorial-narrative` — si es `false`, el pipeline se detiene acá y el item igual pasa a `READY_FOR_REVIEW`.

## `hooks.json` (solo si `narrative_recommended: true`)

```json
{
  "item_id": "793ff158b714",
  "hooks": [
    {"text": "...", "strategy": "...", "based_on": "...", "provenance": "CREATIVE_FRAMING"}
  ]
}
```

`based_on` referencia el hecho o ángulo concreto (de `understanding.json`/`editorial_analysis.json`) del que sale el hook — un hook nunca se inventa sin apoyo trazable.

## `script.json` (solo si `narrative_recommended: true`)

```json
{
  "item_id": "793ff158b714",
  "sections": [
    {"section": "HOOK", "text": "...", "provenance": "CREATIVE_FRAMING"}
  ]
}
```

`section`: `HOOK` | `SETUP` | `CONTEXT` | `DEVELOPMENT` | `TURNING_POINT` | `PAYOFF` | `CLOSING`.

## `scene_plan.json` (solo si `narrative_recommended: true`)

```json
{
  "item_id": "793ff158b714",
  "scenes": [
    {
      "scene_number": 1,
      "narrative_purpose": "...",
      "visual_description": "...",
      "required_media_type": "REAL_IMAGE",
      "text_overlay": "...",
      "duration_estimate_seconds": 4
    }
  ]
}
```

`required_media_type`: `REAL_IMAGE` (foto real de la noticia/fuente) | `GENERATED_IMAGE` (Gemini, Fase 3) | `EDITED_IMAGE` (real editada, Fase 3) | `NO_IMAGE`. Fase 2 solo **decide** qué tipo de media hace falta — no genera ni edita nada, eso es Fase 3 (Media Agent).
