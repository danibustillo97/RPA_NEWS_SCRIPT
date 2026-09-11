---
title: LAB -- Render Planning (Fase 4.2, etapa 3)
status: Fase 4.2 etapa 3 implementada (sin skill/CLI/ejecución todavía)
date: 2026-09-10
---

# Render Planning

Tercera etapa de Fase 4.2. Convierte `animation_plan.json` (etapa 1/2) en `render_plan.json`: por cada shot, la geometría concreta (dimensiones objetivo, padding/crop en píxeles) que un futuro `Renderer` necesitaría — **solo cuando es matemática de escalado pura, derivable de datos reales**. No ejecuta FFmpeg ni ningún motor, no genera video, no llama a ningún proveedor.

## Qué decide esta etapa que Animation Plan todavía no decidía

`AnimationShot.motion` es una etiqueta (`{"type": "SLOW_ZOOM_IN"}`) y `source_transform` solo dice *qué tipo* de transformación hace falta (`EXTEND`, decisión editorial de la skill de Fase 4.1) — ninguno de los dos compromete números. Render Plan sí lo hace, pero únicamente cuando es geometría verificable:

- **`target_width`/`target_height`**: derivados de `target_aspect_ratio` con una tabla acotada de resoluciones estándar (`lab.render.constants.TARGET_DIMENSIONS`, 1080-based) — mismo criterio que `_ASPECT_RATIO_DIMENSIONS` en `cloudflare_flux.py`.
- **`transform_geometry`**: cuando `source_transform.required` es `true` y el `backend` es `FFMPEG_LOCAL`, se calcula a partir de las dimensiones **reales** del asset (`asset_registry.json`, lectura) y las dimensiones objetivo — escalado estándar tipo "fit" (para `EXTEND`/`FIT`) o "cover" (para `CROP`), la misma matemática que usa cualquier editor/motor de video para encajar una imagen en un lienzo de otra proporción. Para `COMPOSE`/`UNKNOWN` (no son geometría pura, son juicio editorial o de IA) queda `computable: false`, **sin ningún número** — nunca se fabrica una cifra que no se puede sostener.
- Para shots `AI_VIDEO` (hoy nunca se producen, ver `docs/LAB_ANIMATION_ENGINE.md`): `transform_geometry` queda `null` a propósito — un proveedor de video con IA resolvería el aspect ratio nativamente (recibiendo `target_aspect_ratio` directo, como ya hacen Gemini/Cloudflare con imágenes hoy), no con matemática de padding.

## La matemática de `compute_transform_geometry()`

**`EXTEND`/`FIT`** (en esta etapa son geométricamente la misma operación — "fit": escalar sin exceder ninguna dimensión, rellenar el resto con padding; ninguno implica extender contenido con IA):

```
scale = min(target_width / source_width, target_height / source_height)
scaled_width = round(source_width * scale)
scaled_height = round(source_height * scale)
pad_x = target_width - scaled_width   (repartido left/right)
pad_y = target_height - scaled_height (repartido top/bottom)
```

**`CROP`** ("cover": escalar para llenar ambas dimensiones, recortar el excedente):

```
scale = max(target_width / source_width, target_height / source_height)
scaled_width = round(source_width * scale)
scaled_height = round(source_height * scale)
crop_x = scaled_width - target_width   (repartido left/right)
crop_y = scaled_height - target_height (repartido top/bottom)
```

**`COMPOSE`/`UNKNOWN`**: `{"type": transform_type, "computable": false}` — sin `scale`, sin `pad_*`/`crop_*`. Recomponer una escena o resolver una decisión que la skill de Fase 4.1 marcó como incierta no es geometría de escalado; queda declarado como pendiente de resolución humana/IA, no una fórmula.

### Caso real verificado (`793ff158b714`, `shot_02`)

`img_001` es un asset real de `1024×1024` (`actual_aspect_ratio: "1:1"`), la secuencia pide `target_aspect_ratio: "9:16"` → `target_width/height: 1080×1920`. `suggested_transform` (Fase 4.1) fue `EXTEND`:

```json
{
  "type": "EXTEND", "computable": true, "operation": "PAD",
  "source_width": 1024, "source_height": 1024,
  "scale_factor": 1.0546875, "scaled_width": 1080, "scaled_height": 1080,
  "pad_left": 0, "pad_right": 0, "pad_top": 420, "pad_bottom": 420
}
```

## Modelo de `render_plan.json`

```json
{
  "render_plan_id": "render_001",
  "animation_plan_id": "anim_001",
  "story_id": "793ff158b714",
  "target_aspect_ratio": "9:16",
  "target_width": 1080,
  "target_height": 1920,
  "status": "DRAFT",
  "shots": [
    {
      "render_shot_id": "render_shot_02",
      "animation_shot_id": "anim_shot_02",
      "shot_id": "shot_02", "scene_id": "scene_02", "asset_id": "img_001",
      "order": 2, "duration_seconds": 4.0,
      "strategy": "DETERMINISTIC", "backend": "FFMPEG_LOCAL",
      "transform_geometry": { "...": "ver arriba" },
      "status": "PENDING",
      "notes": ""
    }
  ],
  "created_at": "..."
}
```

`status` de cada shot es siempre `"PENDING"` en esta etapa — `DONE`/`FAILED` están reservados en `RENDER_SHOT_STATUS` para cuando exista ejecución real (etapa futura), pero esta etapa nunca los produce.

## Reglas de validación (`validate_render_plan(story_id)`)

No lanza — devuelve una lista de errores:

1. **Coherencia**: `animation_plan_id`/`story_id`/`target_aspect_ratio` coinciden con `animation_plan.json`; cada `RenderShot.animation_shot_id` existe ahí, y `shot_id`/`scene_id`/`asset_id`/`order`/`duration_seconds`/`strategy`/`backend` coinciden exactamente con el `AnimationShot` de origen.
2. `backend` nunca se re-decide — debe ser el mismo del `AnimationShot`.
3. `transform_geometry` debe ser `null` si no hace falta (sin transform pendiente, o `backend: AI_VIDEO`).
4. `transform_geometry` no puede ser `null` cuando sí hace falta (`transform_required: true` + `FFMPEG_LOCAL`); `computable` debe coincidir con si `suggested_transform` está en `GEOMETRY_COMPUTABLE_TRANSFORMS` (`CROP`/`FIT`/`EXTEND`).
5. Cuando `computable: true`: dimensiones y `pad_*`/`crop_*` deben ser enteros válidos (positivos / ≥ 0 según corresponda).
6. `status` de cada shot debe ser `"PENDING"`.
7. Orden idéntico al de `animation_plan.json`.
8-10. Estructurales: `lab/render/` nunca importa funciones de escritura de `lab.animation.planner`/`lab.media.registry`/`lab.sequence.planner`, nunca invoca `subprocess` ni ningún SDK de provider.

## Aislamiento

`lab/render/` **lee** `animation_plan.json` (`lab.animation.planner.load`, solo lectura) y `asset_registry.json` (`lab.media.registry.get_asset`, solo lectura) — nunca los escribe, tampoco `sequence.json` ni `media_blueprint.json`. Sin skill, sin comando CLI, sin job registrado todavía (llega junto con la integración de Claude Code, etapa futura). Gemini, Cloudflare, y todo lo anterior de Fase 3/4 quedan sin modificar.

## Verificado con datos reales

`793ff158b714` → `render_plan.json`: `animation_plan_id: "anim_001"`, `target_width/height: 1080×1920`, 5 shots. `shot_02` (único con asset real) queda `backend: FFMPEG_LOCAL`, `transform_geometry.computable: true` con los números exactos de arriba. Los otros 4: `transform_geometry: null`, `status: PENDING`. `validate_render_plan()` → `[]`. `sequence.json`, `asset_registry.json` y `animation_plan.json` quedaron byte-a-byte idénticos antes y después (SHA-256).

## Qué falta (fuera de esta etapa)

Skill + comando CLI de Claude Code para Render Planning (equivalente a la Etapa 2 de Animation Planning), un `Renderer` real (FFmpeg, que traduciría `transform_geometry` a filtros concretos como `scale`/`pad`/`crop` y ejecutaría de verdad), y un `VideoProvider` real (IA) — ninguno implementado todavía.
