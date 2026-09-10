---
title: LAB -- Animation Planning (Fase 4.2, etapa 1)
status: Fase 4.2 etapa 1 implementada (sin skill/CLI/render todavía)
date: 2026-09-10
---

# Animation Planning

Primera etapa de Fase 4.2. Convierte `sequence.json` (Fase 4.1) en `animation_plan.json`: por cada shot, decide si el movimiento se puede resolver de forma determinista (FFmpeg local, sin IA) o si requeriría generación de video con IA — y arma una instrucción de movimiento declarativa. **No ejecuta ningún movimiento, no genera ningún video, no llama a ningún proveedor.**

## Dónde está cada pieza de la arquitectura completa (Sequence → Animation Plan → Render Plan → Renderer/VideoProvider → Video)

| Pieza | Qué hace | Estado |
|---|---|---|
| **Sequence** (`sequence.json`, Fase 4.1) | Qué cuenta la historia y en qué orden — shots, escenas, assets, duración | Implementado |
| **Animation Plan** (`animation_plan.json`, acá) | Cómo se pretende animar cada shot — estrategia (determinista/IA) + movimiento declarativo | Implementado (esta etapa) |
| **Render Plan** | Cómo se ejecutaría físicamente ese movimiento (parámetros concretos de FFmpeg, o request concreto a un VideoProvider) | **No implementado todavía** |
| **Renderer** (FFmpeg local) | Ejecutaría de verdad los movimientos deterministas | **No implementado todavía** |
| **VideoProvider** (IA image-to-video) | Generaría de verdad video con IA | **No implementado todavía** |

Esta etapa es deliberadamente **100% Python determinista, sin skill, sin comando CLI**: la clasificación `DETERMINISTIC` es derivable directo, porque el vocabulario `MOTION_TYPES` que `sequence.json` ya usa (Fase 4.1) *es* exactamente la lista de movimiento determinista — no hace falta criterio editorial para clasificar un movimiento que Fase 4.1 solo permite generar desde ese vocabulario.

## Por qué `decide_strategy()` nunca produce `AI_VIDEO` todavía

`lab.animation.planner.decide_strategy(motion)` es la única función que decide `DETERMINISTIC` vs `AI_VIDEO`. Hoy, **siempre** devuelve `("DETERMINISTIC", "FFMPEG_LOCAL")` para cualquier `motion` válido — porque `lab.sequence.planner.validate_sequence()` (Fase 4.1) ya garantiza que ningún `SequenceShot.motion` real puede ser otra cosa que un valor de `MOTION_TYPES` (`STATIC`/`SLOW_ZOOM_IN`/`SLOW_ZOOM_OUT`/`PAN_*`/`PUSH_IN`/`PULL_OUT`). No existe todavía un criterio (humano o de una futura skill) para decidir cuándo un shot necesita generación de video con IA — esa decisión queda fuera de esta etapa a propósito. `AI_VIDEO` está soportado en el vocabulario y en la validación (una combinación `AI_VIDEO`/`AI_VIDEO` es válida si algún día aparece) pero no se ejercita.

## Modelo de `animation_plan.json`

```json
{
  "animation_plan_id": "anim_001",
  "sequence_id": "seq_001",
  "story_id": "793ff158b714",
  "target_aspect_ratio": "9:16",
  "status": "DRAFT",
  "shots": [
    {
      "animation_shot_id": "anim_shot_02",
      "shot_id": "shot_02",
      "scene_id": "scene_02",
      "asset_id": "img_001",
      "order": 2,
      "duration_seconds": 4.0,
      "strategy": "DETERMINISTIC",
      "backend": "FFMPEG_LOCAL",
      "motion": {"type": "SLOW_ZOOM_IN"},
      "transition_in": "FADE",
      "transition_out": "CUT",
      "source_transform": {
        "required": true,
        "suggested_transform": "EXTEND",
        "status": "PENDING"
      },
      "notes": ""
    }
  ],
  "total_duration_seconds": 17.0,
  "created_at": "2026-09-10T..."
}
```

### Decisiones de diseño (dónde se aparta del ejemplo conceptual original, con motivo)

- **`transition_in`/`transition_out` (dos campos), no un único `transition`.** `SequenceShot` (Fase 4.1) ya los separa — colapsarlos perdería información al copiarlos. `AnimationShot` los hereda tal cual.
- **`motion` en esta etapa solo lleva `{"type": "<MOTION_TYPE>"}`** — un passthrough validado del `motion` del `SequenceShot` correspondiente (mismo vocabulario `lab.sequence.constants.MOTION_TYPES`, importado, no reinventado). No hay todavía una base real para asignar parámetros numéricos de ejecución (escala inicial/final, curva de easing) sin inventarlos — eso es trabajo de un futuro Render Plan, que sí necesita comprometerse a valores concretos para generar un comando de FFmpeg real.
- **`source_transform` es un passthrough fiel** de `transform_required`/`suggested_transform` que la skill de Fase 4.1 ya decidió — nunca se recalcula ni se reinterpreta acá. Se agrega `status: "PENDING"` para dejar explícito que la transformación sigue sin aplicarse.

## Reglas de validación (`validate_animation_plan(story_id)`)

No lanza — devuelve una lista de errores (vacía si es válido):

1. **Coherencia de referencias**: `sequence_id`/`story_id`/`target_aspect_ratio` del plan deben coincidir con el `sequence.json` real; cada `AnimationShot.shot_id` debe existir en `sequence.json`, y sus `scene_id`/`asset_id`/`duration_seconds`/`order`/`transition_in`/`transition_out` deben coincidir exactamente con el `SequenceShot` correspondiente — no alcanza con que "existan en algún lado". Si `asset_id` no es `null`, además se confirma que existe en `asset_registry.json` (lectura, vía `lab.media.registry.get_asset`).
2. **`strategy`/`backend`**: deben ser exactamente el par de `STRATEGY_BACKEND_MAP` (`DETERMINISTIC`→`FFMPEG_LOCAL`, `AI_VIDEO`→`AI_VIDEO`) — cualquier otra combinación es inválida.
3. Si el `SequenceShot` original tiene `transform_required` `false` o ausente (sin asset) → `source_transform` debe ser `null`.
4. Si tiene `transform_required: true` → `source_transform` no puede ser `null`, debe traer `suggested_transform` y `status: "PENDING"` (ningún otro status es válido en esta etapa).
5. `motion.type` debe ser un valor real de `MOTION_TYPES` — nada de campos de ejecución (el schema fijo ya lo garantiza estructuralmente).
6. `duration_seconds` debe ser un número positivo.
7. El orden de los shots (`order`) debe ser **idéntico**, en la misma secuencia, al de `sequence.json` — no solo "sin huecos".
8-10. Estructurales, garantizadas por diseño: `lab/animation/` nunca importa `register_asset`/`next_asset_id`/`init_sequence`, y su único `write_text` es hacia `animation_plan.json` — nunca toca `asset_registry.json`, `media_blueprint.json` ni `sequence.json`.

## Aspect ratio — sin cambios de criterio

`target_aspect_ratio` se copia de `sequence.json`, no se recalcula. `source_transform` es lectura fiel de lo que Fase 4.1 ya decidió comparando `actual_aspect_ratio` (real, del asset) contra el `target_aspect_ratio` de la secuencia — esta etapa no vuelve a hacer esa comparación ni toca `asset_registry.json`.

## Aislamiento (capa puramente aditiva)

`lab/animation/` **lee** `sequence.json` (`lab.sequence.planner.load`, solo lectura) y `asset_registry.json` (`lab.media.registry.get_asset`, solo lectura) — nunca los escribe. No existe ningún comando CLI ni skill todavía, así que tampoco se registra ningún job en `lab/core/job.py` en esta etapa (eso llega junto con el comando, en una etapa futura). Gemini, Cloudflare, y todo `lab/media/*`/`lab/sequence/*` quedan sin modificar.

## Verificado con datos reales

`793ff158b714` → `animation_plan.json`: `sequence_id: "seq_001"`, 5 shots, `total_duration_seconds: 17.0`. `shot_02` (único shot con asset real, `img_001`) queda `strategy: DETERMINISTIC`, `backend: FFMPEG_LOCAL`, `motion: {"type": "SLOW_ZOOM_IN"}`, `source_transform: {"required": true, "suggested_transform": "EXTEND", "status": "PENDING"}` — coherente con lo que `sequence.json` ya declaraba. Los otros 4 shots (sin asset) quedan con `source_transform: null`. `validate_animation_plan()` devuelve `[]`. `asset_registry.json` y `sequence.json` quedaron byte-a-byte idénticos antes y después (verificado por hash SHA-256).

## Qué falta (fuera de esta etapa)

Comando CLI (`/lab-animation-plan`), skill de criterio (solo necesaria el día que `AI_VIDEO` sea una opción real, no antes), Render Planner, `Renderer` (FFmpeg), `VideoProvider` (IA) — todo pendiente, en ese orden, según el plan de 5 etapas de Fase 4.2 ya presentado.
