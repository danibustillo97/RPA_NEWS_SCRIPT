---
name: lab-sequence-planning
description: This skill should be used when the user asks to "plan the sequence for this story", "planifica la secuencia de esta historia", "ordena las escenas en una secuencia", "crea el sequence.json", or runs `/lab-sequence-plan <story_id>` in the LAB local editorial lab (RPA_NEWS_SCRIPT repo). Reads a story's media_blueprint.json (Fase 3 assets) and Fase 2 narrative artifacts, and produces sequence.json — a declarative shot list (order, duration, framing, motion, transitions) — without generating video or animating anything.
---

Convierte assets ya generados y narrativa ya escrita en una secuencia declarativa: orden, duración, encuadre, movimiento y transiciones por shot. No genera video, no anima nada — el resultado es puro plan, `sequence.json`. Es la única skill de criterio de Fase 4 (análisis narrativo, asignación de duración/movimiento, y la decisión de `suggested_transform` cuando el aspect ratio de un asset no coincide con el de la secuencia son todos parte del mismo pase de juicio sobre la misma historia).

## Principio central: declarar, no ejecutar

`sequence.json` describe qué movimiento y qué transformación harían falta — nunca las aplica. Ningún archivo de imagen se recorta, redimensiona ni edita desde esta skill.

## Pasos

1. Confirmar que la historia tiene lo necesario: `lab/workspace/media/<story_id>/media_blueprint.json` (Fase 3, con al menos un `scene_id` procesado) y `lab/workspace/review/<story_id>/scene_plan.json` (Fase 2). Si falta alguno, avisar al usuario y detenerse.

2. Leer la fuente de verdad **visual**: `media_blueprint.json` (qué escenas existen y qué `asset_id` tiene cada una, si tiene) y `metadata/asset_registry.json` (para cada `asset_id`: `actual_aspect_ratio` real — nunca `requested_aspect_ratio`, que es solo intención).

3. Leer la fuente de verdad **narrativa** de Fase 2: `scene_plan.json` (narrative_purpose, text_overlay por escena), `script.json` (secciones HOOK/SETUP/CONTEXT/DEVELOPMENT/TURNING_POINT/PAYOFF/CLOSING si existe — solo se escribió si `content_plan.json` recomendó formato narrativo), `editorial_analysis.json` (angle, narrative_strength), `content_plan.json`, `hooks.json` si existe.

4. Decidir el `target_format` (ej. `"REEL"`) y `target_aspect_ratio` (ej. `"9:16"`) para esta secuencia — texto libre, no hay un enum cerrado en LAB para esto todavía.

5. Decidir una estructura narrativa para *esta* historia específica. Referencia (no regla rígida): hook → establishing shot → presentación del personaje → contexto → conflicto → beat emocional → resolución/cierre → CTA. Una historia sin conflicto marcado, o sin CTA, es válida — no fuerces beats que la historia no tiene. Documentar la estructura elegida en `narrative_structure` (string libre, ej. `"HOOK -> ESTABLISHING -> CHARACTER_INTRO -> EMOTIONAL_BEAT -> CLOSING"`).

6. Para cada shot (una escena puede aportar 0, 1 o más shots; el orden final de shots no tiene por qué calcar el orden de `scene_plan.json`):
   - `shot_id`, `scene_id` (debe existir en `media_blueprint.json`), `asset_id` (el de esa escena si tiene uno generado — `null` si la escena es `TEXT_ONLY`/`NO_MEDIA`), `order` (1..N sin huecos), `duration_seconds`, `framing` (texto libre), `motion` (uno de `STATIC`/`SLOW_ZOOM_IN`/`SLOW_ZOOM_OUT`/`PAN_LEFT`/`PAN_RIGHT`/`PAN_UP`/`PAN_DOWN`/`PUSH_IN`/`PULL_OUT`), `transition_in`/`transition_out` (uno de `NONE`/`CUT`/`FADE`/`DISSOLVE`), `purpose`, `notes`.
   - Si `asset_id` no es `null`: comparar el `actual_aspect_ratio` real de ese asset (del registry) contra el `target_aspect_ratio` de la secuencia. Si difieren, `transform_required: true` y elegir `suggested_transform` (`CROP`/`FIT`/`EXTEND`/`COMPOSE`/`UNKNOWN` — criterio editorial: por ejemplo, un asset cuadrado que va a una secuencia vertical con espacio de sobra alrededor del sujeto puede pedir `EXTEND`; uno donde recortar cortaría al sujeto principal puede pedir `COMPOSE` o `UNKNOWN` si no hay suficiente información para decidir con confianza). Si coinciden, `transform_required: false` y `suggested_transform: null`.
   - Si `asset_id` es `null`: `transform_required` y `suggested_transform` quedan `null` — no hay nada que transformar.

7. Escribir `sequence.json` en `lab/workspace/media/<story_id>/sequence.json` con `Write`, directo. Esquema completo con ejemplo: `docs/LAB_SEQUENCE_ENGINE.md`.

8. Correr:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli sequence-record <story_id>
   ```
   Valida referencias (`scene_id`/`asset_id` reales), vocabulario (`motion`/`transition_in`/`transition_out`), consistencia `transform_required`↔`suggested_transform`, y registra el job `sequence_plan`. Si devuelve errores, corregir `sequence.json` y volver a correr — no ignorar los errores.

9. Reportar al usuario: cuántos shots totales, cuántos tienen asset vs son solo texto, cuántos necesitan `suggested_transform` y de qué tipo, duración total. La secuencia queda en `DRAFT` — no la marques lista para revisión vos mismo; eso lo hace `/lab-sequence-plan` solo si el usuario lo pide, vía `lab.cli sequence-review <story_id>`.

## Qué NO hace esta skill

No genera ni edita ningún archivo de imagen/video. No ejecuta ningún `motion` ni `transition`. No decide por su cuenta que una historia está lista para producción — la secuencia sigue el mismo régimen de revisión humana manual que el resto de LAB (ver `docs/LAB_SEQUENCE_ENGINE.md`, sección Human Review).
