---
title: LAB -- Media Assets (esquemas, Fase 3)
status: Fase 3 implementada
date: 2026-09-10
---

# Esquemas de Fase 3

Todos los artifacts de una historia viven en `lab/workspace/media/<story_id>/`:

```
lab/workspace/media/<story_id>/
  images/
    generated/
    edited/
    real/        (un humano coloca el archivo manualmente -- LAB no lo busca)
    archive/     (idem)
  references/
  metadata/
    asset_registry.json
    visual_style.json
    character_profiles/
      <character_id>.json
  media_plan.json
  generation_requests.json
  media_blueprint.json
```

`video/`, `audio/`, `graphics/`, `thumbnails/` no se crean en Fase 3 -- no hay código que escriba ahí todavía (ver "Fuera de alcance" en `docs/LAB_MEDIA_INTELLIGENCE.md`); se documentan acá como el lugar donde vivirían cuando haya un proveedor real.

## `visual_style.json`

```json
{
  "story_id": "793ff158b714",
  "style_id": "cinematic_documentary",
  "tone": "íntimo, sobrio",
  "lighting": "...",
  "color_language": "...",
  "camera_language": "...",
  "texture": "...",
  "era": "contemporáneo",
  "realism": "photorealistic",
  "reasoning": "..."
}
```

## `character_profiles/<character_id>.json`

```json
{
  "character_id": "jonathan_sia",
  "story_id": "793ff158b714",
  "name": "Jonathan Sia",
  "age_context": "23 años",
  "physical_description": "",
  "wardrobe": "",
  "known_reference_assets": [],
  "visual_notes": "Persona privada real sin foto disponible con derechos claros. No generar una probable semejanza a la persona real -- usar una representación genérica.",
  "continuity_notes": "",
  "provenance": "UNVERIFIED"
}
```

`known_reference_assets` arranca vacío y se llena solo (bootstrap, ver `docs/LAB_MEDIA_INTELLIGENCE.md`) con el primer asset generado de ese personaje.

## `media_plan.json`

Lista de `media_requirement`, uno por escena:

```json
[
  {
    "scene_id": "scene_01",
    "narrative_purpose": "...",
    "visual_purpose": "...",
    "subject": "...", "characters": [], "location": "...", "time_period": "...",
    "action": "...", "emotion": "...", "composition": "...", "camera_concept": "...",
    "lighting": "...", "visual_style_ref": "cinematic_documentary", "aspect_ratio": "9:16",
    "estimated_duration": 3,
    "media_type": "GENERATED_IMAGE",
    "generation_required": true,
    "priority": "high",
    "decision_reasoning": "...",
    "scene_plan_type_override": null
  }
]
```

`scene_plan_type_override` solo se llena cuando el Decision Engine cambia lo que decía el `scene_plan.json` de Fase 2 (ej. `"REAL_IMAGE -> GENERATED_IMAGE porque no hay foto real utilizable de una persona privada identificable"`).

El `aspect_ratio` de acá (y el de `generation_requests.json :: prompt_spec.aspect_ratio`, más abajo) es **intención de planificación** — lo que se va a pedir. No es una afirmación sobre ningún archivo físico todavía (no existe ninguno en esta etapa), así que no hace falta distinguir requested/actual acá — esa distinción es específicamente del `asset_registry.json`, una vez que el archivo real existe y puede (o no) coincidir con lo pedido.

## `generation_requests.json`

```json
{
  "story_id": "793ff158b714",
  "requests": [
    {
      "request_id": "req_scene01_v1",
      "scene_id": "scene_01",
      "operation": "generate",
      "characters": [],
      "prompt_spec": {
        "subject": "...", "action": "...", "environment": "...",
        "composition": "...", "camera": "...", "lighting": "...",
        "mood": "...", "style": "...", "era": "...",
        "constraints": "...", "aspect_ratio": "9:16"
      },
      "references": [{"asset_id": "img_001", "role": "style"}],
      "parent_asset_id": null,
      "prompt_version": 1,
      "status": "PENDING",
      "result_asset_id": null,
      "error": null
    }
  ]
}
```

`operation`: `"generate"` o `"edit"` (si es `"edit"`, `parent_asset_id` es obligatorio). `references[].role`: `character`/`style`/`location`/`object`/`archive`/`previous_generation`. `characters` son los `character_id` de la escena -- se usa para el bootstrap de continuidad, no para el prompt en sí. `lab/media/prompt.py :: build_prompt()` construye el prompt final a partir de `prompt_spec` en el momento de ejecutar -- los campos persisten separados para poder auditar o regenerar sin reconstruir el prompt a mano.

## `asset_registry.json`

Lista append-only, un record por asset realmente generado y guardado (un fallo nunca crea uno):

```json
[
  {
    "asset_id": "img_001", "story_id": "793ff158b714", "scene_id": "scene_02",
    "type": "image", "subtype": "generated",
    "filename": "scene_02-img_001.jpeg", "relative_path": "images/generated/scene_02-img_001.jpeg",
    "mime_type": "image/jpeg", "width": 1024, "height": 1024,
    "requested_aspect_ratio": "9:16", "actual_aspect_ratio": "1:1",
    "source": null, "provider": "cloudflare", "model": "@cf/black-forest-labs/flux-1-schnell",
    "prompt_version": 1, "generation_timestamp": "2026-09-10T...",
    "parent_asset_id": null, "references": [],
    "provenance": "AI_GENERATED", "status": "READY"
  }
]
```

`width`/`height` se calculan abriendo el archivo guardado con Pillow -- nunca se confía ciegamente en lo que reporte la API. Una edición (`provenance: AI_EDITED`) siempre trae `parent_asset_id` apuntando al asset del que partió, y **nunca sobreescribe el archivo original** -- eso es el lineage/versionado (`scene-01-v1`, `scene-01-v2`, ..., todas conservadas).

### `requested_aspect_ratio` vs `actual_aspect_ratio` (deuda técnica cerrada)

Estos dos campos reemplazan lo que originalmente era un único campo `aspect_ratio` — ese campo mezclaba dos cosas distintas y terminó siendo activamente engañoso: guardaba lo que se *pidió* al provider, no lo que el archivo real terminó siendo. El caso real que lo expuso: `flux-1-schnell` no acepta ningún parámetro de tamaño (ver `docs/LAB_MEDIA_INTELLIGENCE.md`) y siempre entrega `1024×1024`, sin importar qué `aspect_ratio` pida el `generation_request` — con el campo viejo, el asset `img_001` (pedido `9:16`, real `1024×1024`) quedaba registrado como `"aspect_ratio": "9:16"`, una afirmación falsa sobre el archivo físico.

- **`requested_aspect_ratio`**: la intención de generación, tal cual venía en `prompt_spec.aspect_ratio` del `generation_request`. Puede ser `null` si nunca se pidió uno explícito — nunca se inventa un valor cuando no existe.
- **`actual_aspect_ratio`**: se **deriva siempre** de `width`/`height` reales (`lab/media/registry.py :: _derive_aspect_ratio()`, fracción reducida por MCD) — nunca del request, nunca del provider, nunca ajustado a mano. Si `width`/`height` no están disponibles, queda `null` en vez de fabricarse.

`width`/`height` en sí **siempre** son la medición real del archivo guardado — nunca se recortan/redimensionan para que coincidan con lo pedido (eso, si se hace alguna vez, es responsabilidad explícita de una fase posterior, no de Fase 3).

`provenance`: `REAL_SOURCE` / `ARCHIVE` / `AI_GENERATED` / `AI_EDITED` / `USER_PROVIDED` / `DERIVED` / `UNKNOWN`. `status`: `READY` / `REJECTED` / `REGENERATE` / `FAILED` -- ciclo de vida del asset, independiente del `WorkflowState` del item (que no cambia en Fase 3).

## `media_blueprint.json`

```json
{
  "story_id": "793ff158b714",
  "visual_identity": {"style_id": "cinematic_documentary"},
  "characters": ["jonathan_sia"],
  "references": [],
  "scenes": [
    {"scene_id": "scene_01", "media_requirement": {"...": "..."}, "assets": ["img_001"]}
  ],
  "status": "PLANNED"
}
```

Artifact conector, liviano -- referencia por ID, no duplica el contenido de `media_plan.json` ni de `asset_registry.json`. Punto de extensión de Fase 4: cada entrada de `scenes[]` va a ganar una clave `sequence` (aditiva, no implementada todavía).

## Jobs

Ver `docs/LAB_JOBS.md`. `media_plan` se registra vía `record_job()` (es Claude reasoning, como las etapas editoriales de Fase 2). `media_generation`/`media_edit`/`media_retry` se registran vía `create_and_run()` -- uno por `generation_request` ejecutado, código determinístico, igual que `run_scraper`.
