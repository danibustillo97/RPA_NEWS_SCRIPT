---
name: lab-render-planning
description: This skill should be used when the user asks to "plan the render for this story", "planifica el render de esta historia", "genera el render plan", "convierte el animation plan en un plan de render", or runs `/lab-render-plan <story_id>` in the LAB local editorial lab (RPA_NEWS_SCRIPT repo). Reads a story's animation_plan.json (Fase 4.2 etapa 1/2) and produces render_plan.json via the existing lab/render/ planner — target resolution and, when it is pure scale geometry (CROP/FIT/EXTEND), the exact padding/crop pixel values a future Renderer would need. Never runs FFmpeg, never generates video, never calls any provider, never modifies animation_plan.json/sequence.json/the Asset Registry.
---

Convierte `animation_plan.json` (Fase 4.2 etapa 1/2) en `render_plan.json` invocando el Render Planner ya implementado en `lab/render/` (Fase 4.2 etapa 3) — esta skill **no decide nada por su cuenta ni duplica ninguna lógica**: toda la matemática de geometría (dimensiones objetivo, padding/crop) ya existe en Python puro (`lab.render.planner`), probada con 24 tests. El trabajo de esta skill es orquestar esa capa desde Claude Code, explicar el resultado en términos claros, y respetar el régimen de revisión humana — no ejecutar FFmpeg, no generar video, no llamar a ningún proveedor, no aprobar nada automáticamente.

## Por qué existe una skill si la lógica ya es determinista

`lab.render.planner.compute_transform_geometry()` es matemática de escalado estándar (fit/cover) aplicada a números reales (dimensiones del asset en `asset_registry.json`, tabla de resoluciones objetivo) — no hace falta criterio editorial para eso cuando el `suggested_transform` ya es `CROP`/`FIT`/`EXTEND` (ver `docs/LAB_RENDER_ENGINE.md`). Esta skill es el "front door" estable de Claude Code hacia esa capa: si en el futuro se agrega ejecución real (un `Renderer` de FFmpeg, o resolver `COMPOSE`/`UNKNOWN` con criterio editorial/IA), esa lógica se agregará en `lab/render/` sin cambiar la superficie que ve el usuario (`/lab-render-plan`). Por ahora, la skill solo invoca y reporta.

## Sequence vs Animation Plan vs Render Plan vs ejecución real

- **Sequence** (`sequence.json`, Fase 4.1): **qué** cuenta la historia y en qué orden — shots, escenas, assets, duración, movimiento y transición como etiquetas de intención.
- **Animation Plan** (`animation_plan.json`, Fase 4.2 etapa 1/2): **cómo se pretende** animar cada shot — estrategia (`DETERMINISTIC`/`AI_VIDEO`), backend previsto (`FFMPEG_LOCAL`/`AI_VIDEO`), `motion`, y la necesidad de transformación de aspect ratio heredada fielmente de la Sequence — todavía declarativo.
- **Render Plan** (`render_plan.json`, esta etapa): **con qué números concretos** se ejecutaría eso — resolución objetivo (`target_width`/`target_height`) y, solo cuando es geometría pura (`CROP`/`FIT`/`EXTEND`), los píxeles exactos de escalado/padding/crop. Para `COMPOSE`/`UNKNOWN` queda `computable: false`, sin ningún número — eso sigue sin resolverse. **Sigue sin ejecutarse nada.**
- **Ejecución real** (`Renderer` FFmpeg, `VideoProvider` de IA): **no implementado todavía** — etapa futura. Esta skill nunca invoca FFmpeg ni ningún SDK de proveedor.

## Vocabulario real — geometría computable vs no computable

`lab/render/constants.py` define hoy exactamente:

- `GEOMETRY_COMPUTABLE_TRANSFORMS = {"CROP", "FIT", "EXTEND"}` — escalado estándar (fit/cover), calculable sin criterio editorial a partir de dimensiones reales.
- `TARGET_DIMENSIONS`: tabla acotada `"1:1"→1080×1080`, `"9:16"→1080×1920`, `"16:9"→1920×1080`, `"4:5"→1080×1350`, `"3:4"→1080×1440`; fuera de la tabla cae al default `1080×1080` — mismo criterio que la tabla equivalente en `cloudflare_flux.py`.
- **`COMPOSE`/`UNKNOWN` no son geometría pura** (son juicio editorial o de IA) — `transform_geometry` queda `{"type": ..., "computable": false}`, **nunca se fabrica un número** para ellos. Esta skill nunca intenta "adivinar" esos valores ni los completa a mano.

## Reglas estrictas (ya aplicadas por `validate_render_plan()`, la skill nunca las contradice)

- **`backend` nunca se re-decide acá** — debe ser exactamente el mismo que el `AnimationShot` de origen.
- **`transform_geometry` es `null` si no hace falta** (sin transform pendiente, o `backend: AI_VIDEO` — un proveedor de IA resolvería el aspect ratio nativamente, no con padding).
- **`transform_geometry` nunca queda `null` cuando sí hace falta** (`source_transform.required: true` + `backend: FFMPEG_LOCAL`).
- **`status` de cada shot es siempre `"PENDING"`** en esta etapa — nada se ejecutó todavía.
- **No se modifica `animation_plan.json`, `sequence.json` ni `asset_registry.json`** — `lab/render/` solo los lee.
- **No se aprueba nada automáticamente**: `render_plan.json` queda en `status: "DRAFT"` al correr esta skill.

## Pasos

1. Identificar el `story_id` (de `$ARGUMENTS` o preguntarle al usuario).
2. Confirmar que existe `lab/workspace/media/<story_id>/animation_plan.json` (Fase 4.2 etapa 1/2 ya corrida). Si no existe, avisar al usuario y sugerir `/lab-animation-plan <story_id>` primero — no inventar un animation plan.
3. Ejecutar:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli render-plan <story_id>
   ```
   Este comando hace todo el trabajo real: llama a `lab.render.planner.init_render_plan()` (lee `animation_plan.json`, calcula dimensiones objetivo y geometría, arma `render_plan.json`, lo guarda), corre `validate_render_plan()`, registra el job `render_plan`, e imprime un resumen completo. La skill no reimplementa nada de esto en el chat — solo lo invoca y reporta.
4. Reportar al usuario, en texto claro (no pegar el JSON crudo salvo que lo pida):
   - `story_id`, `animation_plan_id`, `target_aspect_ratio`, `target_width`/`target_height`.
   - Por cada shot: `backend`, y si tiene `transform_geometry` (computable o no, y con qué valores).
   - Si `validate_render_plan()` devolvió errores: mostrarlos tal cual, explicar que el plan no quedó validado, y no intentar corregirlos automáticamente sin que el usuario lo pida.
   - Que el plan quedó en `DRAFT` — listo para que el usuario lo revise, sin ningún paso de aprobación automática ni ejecución real.

## Qué NO hace esta skill

No genera video. No ejecuta FFmpeg real ni ningún otro motor. No llama a ninguna API externa (Gemini, Cloudflare, o cualquier VideoProvider futuro). No crea ni modifica assets en `asset_registry.json`. No modifica `animation_plan.json` ni `sequence.json`. No inventa números para `COMPOSE`/`UNKNOWN`. No aprueba ni rechaza el plan — eso es revisión humana, manual, fuera de LAB.
