---
name: lab-editorial-storycraft
description: This skill should be used when the user asks to "find the story in this news item", "encuentra la historia de esta noticia", "analiza el ángulo editorial", "decide el formato de contenido", "haz el content plan", or runs `/lab-find-stories <item_id>` / the second stage of `/lab-process-news <item_id>` in the LAB local editorial lab (RPA_NEWS_SCRIPT repo). Produces editorial_analysis.json, story_concepts.json, and content_plan.json for a LAB item.
---

Decide por qué (si es que) una noticia ya entendida importa, si tiene una historia narrable, y qué formato conviene. Es el segundo cluster del pipeline editorial de Fase 2 (`docs/LAB_EDITORIAL_INTELLIGENCE.md`) — depende de `understanding.json` ya escrito por `lab-editorial-understanding`.

## Regla central: "no hay historia" es un resultado válido

No forzar un ángulo narrativo donde no lo hay. Una noticia puramente informativa (precios, horarios, decretos, rankings) puede — y debe — terminar en `story_concepts.json :: has_story: false` con `reason_if_not` explicando por qué, y `content_plan.json :: narrative_recommended: false`. Eso no es un fallo de la skill, es el juicio editorial correcto. Ver `docs/LAB_EDITORIAL_INTELLIGENCE.md` sección "No hay historia es una salida válida".

## Pasos

1. Confirmar que el item está en `PROCESSING` y que `understanding.json` (y de preferencia `research.json`/`fact_check.json`) ya existen en `item_dir`:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli editorial-show <item_id>
   ```
   Si `understanding.json` no existe todavía, no seguir — correr `lab-editorial-understanding` primero (avisar al usuario).

2. Leer `understanding.json`, `research.json` y `fact_check.json` completos antes de razonar — el análisis editorial se construye sobre lo ya entendido y verificado, no sobre el `content` crudo de nuevo.

3. Escribir `editorial_analysis.json` (esquema en `docs/LAB_ARTIFACTS.md`): por qué importa la noticia (`why_it_matters`), el ángulo (`angle`: `NEWS_ANGLE`/`STORY_ANGLE`/`HUMAN_ANGLE`/`HISTORICAL_ANGLE`/`EXPLAINER_ANGLE`/`CONTROVERSY_ANGLE`/`UNKNOWN_FACT_ANGLE`/`DOCUMENTARY_ANGLE`/`NONE`), y qué tan fuerte es narrativamente (`narrative_strength`: `HIGH`/`MEDIUM`/`LOW`/`NONE`), con el razonamiento explícito en `reasoning`.

4. Escribir `story_concepts.json`: si `narrative_strength` no es `NONE`, proponer 1-3 conceptos de historia concretos (título, resumen, ángulo), cada uno marcado `provenance: CREATIVE_FRAMING` (son decisiones editoriales, no hechos). Si no hay ángulo aprovechable, `has_story: false` + `reason_if_not`, `concepts: []`.

5. Escribir `content_plan.json`: qué formatos recomendar (`NEWS`/`EXPLAINER`/`REEL`/`STORY`/`CAROUSEL`/`NONE`, cada uno con su razón) y `narrative_recommended` (booleano — decide si corre `lab-editorial-narrative` después). Este archivo es el que `lab.cli editorial-review` exige como uno de los 3 artifacts mínimos, así que siempre se escribe, haya o no historia.

6. Registrar la etapa:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli editorial-stage-done <item_id> STORYCRAFT
   ```

7. Reportar al usuario: el ángulo encontrado (o la ausencia de uno, sin tratarlo como problema), la fuerza narrativa, y el formato recomendado.

## Cuándo se detiene esta skill sola

Si `/lab-find-stories` la invocó sola, termina acá — no sigue automáticamente a `lab-editorial-narrative` aunque `narrative_recommended` sea `true`. Esa decisión de continuar la toma `/lab-process-news` (que sí encadena las 3 skills) o el usuario, corriendo `/lab-generate-hooks` / `/lab-create-script` explícitamente.
