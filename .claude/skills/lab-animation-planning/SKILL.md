---
name: lab-animation-planning
description: This skill should be used when the user asks to "plan the animation for this story", "planifica la animacion de esta historia", "genera el animation plan", "convierte la secuencia en un plan de animacion", or runs `/lab-animation-plan <story_id>` in the LAB local editorial lab (RPA_NEWS_SCRIPT repo). Reads a story's sequence.json (Fase 4.1) and produces animation_plan.json via the existing lab/animation/ planner — a declarative per-shot animation strategy (DETERMINISTIC/AI_VIDEO), backend, and motion instruction. Never generates video, never calls any provider, never modifies sequence.json or the Asset Registry.
---

Convierte `sequence.json` (Fase 4.1) en `animation_plan.json` invocando el Animation Planner ya implementado en `lab/animation/` (Fase 4.2 etapa 1) — esta skill **no decide nada por su cuenta ni duplica ninguna lógica**: toda la clasificación de estrategia, el armado de `motion`/`source_transform`, y las validaciones ya existen en Python puro (`lab.animation.planner`), probadas con 28 tests. El trabajo de esta skill es orquestar esa capa desde Claude Code, explicar el resultado en términos claros, y respetar el régimen de revisión humana — no generar video, no llamar a ningún proveedor, no aprobar nada automáticamente.

## Por qué existe una skill si la lógica ya es determinista

Hoy `lab.animation.planner.decide_strategy()` siempre resuelve a `DETERMINISTIC`/`FFMPEG_LOCAL` — no hace falta juicio editorial para eso (ver `docs/LAB_ANIMATION_ENGINE.md`). Esta skill es el "front door" estable de Claude Code hacia esa capa: cuando en una etapa futura `AI_VIDEO` se vuelva una decisión real (qué shots necesitan generación de video con IA), esa lógica se agregará acá o en `lab/animation/` sin cambiar la superficie que ve el usuario (`/lab-animation-plan`). Por ahora, la skill solo invoca y reporta.

## Sequence vs Animation Plan vs Render Plan

- **Sequence** (`sequence.json`, Fase 4.1, ya implementada): **qué** cuenta la historia y en qué orden — shots, escenas, assets, duración, movimiento y transición como etiquetas de intención.
- **Animation Plan** (`animation_plan.json`, esta etapa): **cómo se pretende** animar cada shot — por cada uno, una estrategia (`DETERMINISTIC` o `AI_VIDEO`) y un backend de ejecución previsto (`FFMPEG_LOCAL` o `AI_VIDEO`), más la instrucción de movimiento (`motion`) y la necesidad de transformación de aspect ratio (`source_transform`) heredadas fielmente de la Sequence — **todavía declarativo, nada se ejecuta**.
- **Render Plan**: cómo se ejecutaría físicamente eso (parámetros concretos de FFmpeg, o un request concreto a un proveedor de video). **No implementado todavía** — etapa futura.

## Estrategias y backends — vocabulario real, no aspiracional

`lab/animation/constants.py` define hoy exactamente:

- `ANIMATION_STRATEGIES = {"DETERMINISTIC", "AI_VIDEO"}`
- `RENDER_BACKENDS = {"FFMPEG_LOCAL", "AI_VIDEO"}`
- Única combinación válida por estrategia: `DETERMINISTIC` → `FFMPEG_LOCAL`, `AI_VIDEO` → `AI_VIDEO`.

**Nota**: si en algún momento se pide `HYBRID`/`NONE` como estrategias o `VIDEO_PROVIDER`/`NONE` como backends, esos valores **no existen todavía** en `lab/animation/constants.py` — agregarlos sería modificar la etapa 1 ya cerrada y commiteada (`659b2f8`), algo que esta skill tiene explícitamente prohibido hacer por su cuenta. Si hace falta ese vocabulario ampliado, es una decisión a tomar explícitamente con el usuario antes de tocar `lab/animation/constants.py` — la skill documenta y usa lo que existe, no inventa lo que falta.

## Reglas estrictas (ya aplicadas por `validate_animation_plan()`, la skill nunca las contradice)

- **`AI_VIDEO` nunca se convierte automáticamente en `FFMPEG_LOCAL`** (ni al revés) — `validate_animation_plan()` rechaza cualquier combinación fuera de `DETERMINISTIC`↔`FFMPEG_LOCAL` / `AI_VIDEO`↔`AI_VIDEO`.
- **Si `SequenceShot.transform_required` es `false` (o el shot no tiene asset), `source_transform` debe ser `null`** — nunca se inventa una necesidad de transformación que la Sequence no declaró.
- **El Animation Plan es puramente declarativo** — `motion` es una etiqueta (`{"type": "SLOW_ZOOM_IN"}`), no un comando ejecutable. Nada de esto genera un frame de video.
- **No se genera ningún video, no se llama a Gemini, Cloudflare ni ningún VideoProvider, no se introduce FFmpeg real.**
- **No se registran assets ni se modifica `asset_registry.json`** — `lab/animation/` solo lee el registry (para confirmar que un `asset_id` referenciado existe), nunca escribe en él.
- **No se modifica `sequence.json`** — solo se lee.
- **No se aprueba nada automáticamente**: `animation_plan.json` queda en `status: "DRAFT"` al correr esta skill. No existe (ni se debe inventar) un mecanismo de aprobación automática — la revisión sigue siendo manual, fuera de LAB, igual que en el resto del sistema.

## Pasos

1. Identificar el `story_id` (de `$ARGUMENTS` o preguntarle al usuario).
2. Confirmar que existe `lab/workspace/media/<story_id>/sequence.json` (Fase 4.1 ya corrida). Si no existe, avisar al usuario y sugerir `/lab-sequence-plan <story_id>` primero — no inventar una secuencia.
3. Ejecutar:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli animation-plan <story_id>
   ```
   Este comando hace todo el trabajo real: llama a `lab.animation.planner.init_animation_plan()` (lee `sequence.json`, arma `animation_plan.json`, lo guarda), corre `validate_animation_plan()`, registra el job `animation_plan`, e imprime un resumen completo (ver abajo). La skill no reimplementa nada de esto en el chat — solo lo invoca y reporta.
4. Reportar al usuario, en texto claro (no pegar el JSON crudo salvo que lo pida):
   - `story_id`, `sequence_id`, cantidad de shots, duración total.
   - Por cada shot: estrategia, backend, `motion`, y si tiene `source_transform` pendiente (y cuál).
   - Si `validate_animation_plan()` devolvió errores: mostrarlos tal cual, explicar que el plan no quedó validado, y no intentar corregirlos automáticamente sin que el usuario lo pida.
   - Que el plan quedó en `DRAFT` — listo para que el usuario lo revise, sin ningún paso de aprobación automática.

## Qué NO hace esta skill

No genera video. No llama a ninguna API externa (Gemini, Cloudflare, o cualquier VideoProvider futuro). No introduce FFmpeg real. No crea ni modifica assets en `asset_registry.json`. No modifica `sequence.json`. No decide por su cuenta ampliar el vocabulario de estrategias/backends. No aprueba ni rechaza el plan — eso es revisión humana, manual, fuera de LAB.
