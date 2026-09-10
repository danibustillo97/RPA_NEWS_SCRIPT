---
title: LAB -- Media Intelligence (Fase 3)
status: Fase 3 implementada
date: 2026-09-10
---

# Media Intelligence / Media Agent

Fase 3 toma una historia ya aprobada editorialmente por Fase 2 (`scene_plan.json` + `script.json` + `editorial_analysis.json` + `content_plan.json`, en `lab/workspace/review/<story_id>/`) y decide, escena por escena, que recurso visual hace falta -- y para las que necesitan imagen generada o editada, la genera de verdad (Gemini o Cloudflare Workers AI/FLUX.1 schnell, seleccionable por configuración — ver "Providers" más abajo), la guarda, y registra su procedencia. LAB no es un generador de imagenes: es una fabrica de historias que tiene **criterio** sobre que crear.

> **Primer asset real generado**: `793ff158b714` / escena `scene_02` / `img_001`, vía Cloudflare Workers AI + `@cf/black-forest-labs/flux-1-schnell` — ver "Hallazgo real" más abajo.

## Principio central: no generar una imagen por escena automáticamente

Primero se decide que necesita la escena. No todas necesitan imagen. No toda imagen debe ser generada -- si existe una foto real utilizable, puede ser preferible a generar una. Este criterio vive en la skill `lab-media-planning`, no en codigo Python (el codigo ejecuta lo que la skill decidio, nunca decide el).

## Arquitectura

```
Claude Code (orquestador)
   |
   v  UNA sola skill de juicio (no nueve agentes)
skill: lab-media-planning
   (Media Analysis + Decision Engine + Referencias + Continuidad de
    personajes + Identidad visual + Prompt Engineering -- un mismo pase
    de razonamiento por historia)
   | escribe directo con Write:
   v
lab/workspace/media/<story_id>/
   metadata/visual_style.json
   metadata/character_profiles/<character_id>.json
   media_plan.json            (media_requirement por escena, con decision_reasoning)
   generation_requests.json   (prompt_spec estructurado, no un string gigante)
   |
   |  lab.cli media-record-plan <story_id>  (bookkeeping + resumen de costo-control)
   v
lab/media/  (Python -- SOLO ejecucion deterministica)
   providers/resolver.py       ->  resolve_media_provider("gemini"|"cloudflare")
   providers/gemini_image.py   ->  Gemini real
   providers/cloudflare_flux.py -> Cloudflare Workers AI (FLUX.1 schnell) real
   storage/local.py            ->  guarda el archivo fisico
   registry.py                 ->  asset_registry.json
   blueprint.py                 ->  media_blueprint.json
   |  lab.cli media-generate <story_id> [--provider gemini|cloudflare]
   v
Assets fisicos en lab/workspace/media/<story_id>/images/{generated,edited,real}/
   + asset_registry.json y media_blueprint.json actualizados
   |
   v
READY_FOR_REVIEW  (el WorkspaceItem NO cambia de estado -- ver seccion "Human Review")
```

Por que una sola skill: a diferencia de Fase 2 (entender/investigar, juzgar el angulo, escribir el guion son 3 modos de razonamiento genuinamente distintos), decidir que necesita cada escena, con que estilo, con que referencias, y como redactar el prompt es un mismo pase de juicio visual sobre la misma historia. La generacion real (llamar a Gemini, escribir el archivo, registrar metadata) es mecanica y deterministica -- vive en Python + CLI, igual que Fase 1 (`lab/ingestion/`) y la mitad "bookkeeping" de Fase 2 (`lab/editorial/pipeline.py`).

## Decision Engine

La skill decide `media_type` por escena con este criterio (ver `.claude/skills/lab-media-planning/SKILL.md` para el detalle operativo):

| Tipo | Cuándo |
|---|---|
| `REAL_IMAGE` | Existe una foto real utilizable con derechos claros (raro en este pipeline -- LAB no busca fotos externas automáticamente, ver "Fuera de alcance") |
| `GENERATED_IMAGE` | El momento no tiene material real disponible pero vale la pena representarlo |
| `EDITED_IMAGE` | Conviene partir de un asset ya generado y transformarlo (otro aspect ratio, otra iluminación) |
| `ARCHIVE_MEDIA` | Hace falta un documento histórico (identificado, no resuelto automáticamente) |
| `VIDEO` / `GENERATED_VIDEO` | La escena necesita movimiento (vocabulario preparado, sin proveedor todavía) |
| `AUDIO` | Sonido/narración (vocabulario preparado, sin proveedor todavía) |
| `GRAPHIC` | Representa datos (vocabulario preparado, sin proveedor todavía) |
| `TEXT_ONLY` / `NO_MEDIA` | La narración funciona sin visual |

**Anular el `scene_plan.json` de Fase 2 con criterio propio es esperado, no un error.** Caso real probado: la escena 2 de `793ff158b714` (Jonathan Sia) venía marcada `REAL_IMAGE` en Fase 2, pero no existe una foto real de esa persona privada con derechos claros -- el Decision Engine la reclasifica a `GENERATED_IMAGE` (representación genérica, nunca presentada como un retrato real de él) y dejó `scene_plan_type_override` en `media_plan.json` explicando el porqué.

## Identidad visual y continuidad de personajes

`visual_style.json` se decide una sola vez por historia (tono, iluminación, lenguaje de color/cámara, textura, época, realismo) y se reusa en todas las escenas que generan/editan -- para que la historia no salte de un estilo a otro escena por escena sin que la propia historia lo justifique.

`character_profiles/<character_id>.json` guarda lo que la fuente realmente sostiene sobre cada personaje (`physical_description`, `wardrobe`, etc., con su `provenance` -- misma taxonomía NO INVENTAR de Fase 2: `SOURCE_FACT`/`VERIFIED_CONTEXT`/`INFERENCE`/`CREATIVE_FRAMING`/`UNVERIFIED`). La primera imagen generada de un personaje se vuelve automáticamente su primera entrada en `known_reference_assets` (lo hace `lab/media/generation.py` después de una generación exitosa) -- las escenas siguientes con el mismo personaje reusan esa referencia (`generate_from_references()`), dando continuidad visual sin que cada llamada a Gemini sea independiente.

## Providers: Gemini + Cloudflare (coexisten, no se reemplazan)

Media Agent (`lab/media/generation.py`) nunca importa un provider concreto -- solo llama a `lab.media.providers.resolver :: resolve_media_provider(name=None)`, que lee `LAB_MEDIA_PROVIDER` del entorno (o el override puntual `--provider`/`params["provider"]`) y devuelve una instancia de `MediaProvider`. Agregar un provider nuevo nunca toca `generation.py`.

**Selección**: `LAB_MEDIA_PROVIDER=gemini` (default) o `LAB_MEDIA_PROVIDER=cloudflare` en `lab/config/.env`; o puntual por corrida con `lab.cli media-generate <story_id> --provider cloudflare`. **Sin fallback automático**: si el provider configurado falla, el `generation_request` queda `FAILED` con el error real -- nunca reintenta en silencio con el otro provider (así se sabe qué provider produjo, o intentó producir, cada asset).

### Gemini (`lab/media/providers/gemini_image.py`)

SDK oficial `google-genai`, vía `client.models.generate_content(model=..., contents=[...], config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio=...)))`. Modelo: `lab/config/settings.py :: GEMINI_IMAGE_MODEL` (default `gemini-3.1-flash-image`, override `LAB_GEMINI_IMAGE_MODEL`). Referencias/imagen base van como `types.Part.from_bytes(data=..., mime_type=...)` en `contents`. `GEMINI_API_KEY` desde entorno/`.env`, nunca hardcodeada ni logueada.

### Cloudflare Workers AI / FLUX.1 schnell (`lab/media/providers/cloudflare_flux.py`)

REST API directa (sin SDK) — `POST https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{modelo}`, header `Authorization: Bearer {CLOUDFLARE_API_TOKEN}`. Modelo habilitado hoy: `lab/config/settings.py :: CLOUDFLARE_IMAGE_MODEL` (default `@cf/black-forest-labs/flux-1-schnell`, override `CLOUDFLARE_IMAGE_MODEL`) — **`flux-2-dev` quedó descartado** (ver "Hallazgo real" más abajo) y no se reintenta.

**Dos formatos de request, verificados por separado y NO intercambiables** (el payload de un modelo no sirve para el otro):
- **Sin imágenes de entrada** (el caso de `flux-1-schnell`, que no soporta imagen de entrada en absoluto): `Content-Type: application/json`, body `{"prompt": "...", "steps": 4}`. Sin `width`/`height` — el modelo no los acepta; la dimensión real de salida se mide del archivo decodificado (Pillow), no se asume. `steps` default 4, máximo 8 (documentado oficialmente).
- **Con imágenes de entrada** (modelos multi-referencia, ej. el descartado `flux-2-dev`): `multipart/form-data`, `prompt`/`width`/`height`/`steps` como campos de texto + `input_image_0`..`input_image_3` binarios. Camino conservado en el código (`_call_multipart`) por si se habilita un modelo multi-referencia más adelante, pero no ejercitado en esta fase.

Respuesta (igual para ambos formatos): sobre estándar de la API v4 de Cloudflare, `{"result": {"image": "<base64>"}, "success": true/false, "errors": [...]}`.

Limitaciones conocidas de FLUX.1 schnell: ver sección dedicada más abajo ("Limitaciones conocidas de FLUX.1 schnell (consolidado)"), junto con cómo eso llevó a distinguir `requested_aspect_ratio` de `actual_aspect_ratio` en el Asset Registry.

### Providers y `MediaProvider`

Ambos implementan la misma interfaz (`generate()`/`edit()`/`generate_from_references()` → `MediaResult`) y declaran `name` (`"gemini"`/`"cloudflare"`), usado para el campo `provider` del asset registrado. Agregar un tercer provider es: una clase nueva en `lab/media/providers/`, una entrada en `MEDIA_PROVIDERS` (`lab/media/constants.py`) y en `resolve_media_provider()` — nada más cambia.

## Storage

`lab/media/storage/` abstrae dónde vive el archivo físico (`StorageProvider`: `save()`/`read()`/`exists()`/`url_or_path()`). Hoy solo existe `LocalStorageProvider` contra `lab/workspace/media/<story_id>/` -- un `S3StorageProvider`/`AzureBlobStorageProvider` futuro se conecta sin tocar `lab/media/generation.py`.

## Asset Registry y provenance

Ver `docs/LAB_MEDIA_ASSETS.md` para el esquema completo. Un fallo de generación **nunca** crea un registro de asset -- solo un `generation_request` en `FAILED` con su error, y un job `FAILED`. Cada asset registra su `provenance` (`REAL_SOURCE`/`ARCHIVE`/`AI_GENERATED`/`AI_EDITED`/`USER_PROVIDED`/`DERIVED`/`UNKNOWN`) y, si es una edición, su `parent_asset_id` -- nunca se sobreescribe un archivo existente.

## Human Review

Fase 3 también termina en `READY_FOR_REVIEW` -- el `WorkspaceItem` **no cambia de estado** (sigue siendo el mismo `READY_FOR_REVIEW` que dejó Fase 2; Fase 3 no introduce ningún `WorkflowState` nuevo en `lab/core/workspace.py`). Lo que cambia es que ahora el item tiene un `media_blueprint.json` con assets reales asociados. Cada asset tiene su propio ciclo de vida independiente en `asset_registry.json :: status` (`READY`/`REJECTED`/`REGENERATE`/`FAILED`) -- rechazar o regenerar un asset no mueve el item entero, ni borra versiones anteriores (ver lineage en `docs/LAB_MEDIA_ASSETS.md`).

## Control de costos

`/lab-media-plan` (o el CLI `media-record-plan`) siempre corre antes de gastar nada -- imprime cuántas escenas hay de cada tipo y cuántas requieren generación real, para que el humano decida si sigue antes de que `/lab-generate-media` llame de verdad a Gemini (costo real por llamada).

## Punto de extensión para Fase 4 (actualizado -- decisión real, no la original)

Esta sección originalmente anticipaba que Fase 4 agregaría una clave `sequence` a cada entrada de `media_blueprint.json :: scenes[]`. **Eso cambió al implementar Fase 4**: una secuencia ordena *shots* a través de toda la historia y un shot no corresponde necesariamente 1:1 con una escena, así que anidarlo en `scenes[]` no encajaba. Fase 4 usa un artifact separado, `sequence.json` (mismo directorio que `media_blueprint.json`), con `shots[]` como lista plana referenciando `scene_id`/`asset_id` por ID — `media_blueprint.json` no se modificó. Ver `docs/LAB_SEQUENCE_ENGINE.md` para el diseño completo y el razonamiento del cambio.

## Fuera de alcance de Fase 3

- Secuenciación/animación (Fase 4), ensamblaje de video/audio/subtítulos/empaquetado final (Fase 5).
- Export/manifest hacia Production News e import automático.
- `S3StorageProvider`/`AzureBlobStorageProvider` -- solo la interfaz.
- Generación/consecución real de `VIDEO`/`GENERATED_VIDEO`/`AUDIO`/`GRAPHIC`/`ARCHIVE_MEDIA` -- el Decision Engine puede asignar estos tipos, pero no hay proveedor que los ejecute todavía.
- Búsqueda automática de imágenes reales/archivo en fuentes externas -- si `REAL_IMAGE`/`ARCHIVE_MEDIA` es la decisión correcta, un humano coloca el archivo manualmente en `images/real/` o `images/archive/`.
- Cambios a `lab/core/workspace.py` -- ningún `WorkflowState` nuevo.

## Comandos

`/lab-media-plan <story_id>`, `/lab-generate-media <story_id>`, `/lab-media-status <story_id>` -- ver `.claude/commands/`. CLI subyacente: `lab.cli media-init/media-record-plan/media-generate/media-status`. `media-generate` acepta `--provider {gemini,cloudflare}` como override puntual del provider configurado.

## Tests

`lab/tests/` (pytest, dependencia solo de desarrollo en `lab/requirements-dev.txt`) cubre resolución de provider, construcción del request de Cloudflare, headers de autenticación, selección de modelo, manejo de errores HTTP/red/respuesta inválida, y aislamiento entre providers — todo con mocks, cero llamadas reales. Correr con `lab/.venv/Scripts/python.exe -m pytest lab/tests/ -v`.

## Hallazgo abierto: billing de Google Cloud (Gemini, no es un bug de LAB)

Probado en la sesión de implementación con una `GEMINI_API_KEY` real: la llamada real a `client.models.generate_content(...)` devuelve `429 RESOURCE_EXHAUSTED` con `limit: 0` para el tier gratuito, en **todos** los modelos de imagen probados (`gemini-3.1-flash-image`, `gemini-2.5-flash-image`) y con **dos** API keys distintas del usuario -- confirma que es una restricción a nivel de proyecto de Google Cloud (los modelos de generación de imagen requieren billing habilitado), no algo resoluble cambiando de modelo o de key desde LAB. Cuando el usuario habilite billing, `/lab-generate-media <story_id> --provider gemini` retoma sin necesidad de replanificar nada.

## Hallazgo real: FLUX.2 dev descartado, FLUX.1 schnell funciona (no fue un bug de LAB)

Primera ronda de pruebas reales con `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN` reales, reusando el `generation_request` real `req_scene02_v1` de `793ff158b714`: **4 intentos** contra `@cf/black-forest-labs/flux-2-dev` (25 steps a 768×1344; 300s de timeout de cliente a 768×1344; 8 steps a 768×1344; 8 steps a 576×1024) terminaron los 4 en `HTTP 408` del lado de Cloudflare (`"AiError: Request timeout"`, código `3046`) después de 4-5 minutos cada uno — ni el número de steps ni la resolución cambiaron el resultado. Un 5to intento diagnóstico contra `@cf/black-forest-labs/flux-1-schnell` (mismo request, mismas credenciales) respondió en ~1 segundo con `HTTP 400` ("Request body is not valid json") — confirmó que credenciales/red funcionan bien, y que el 400 era porque el provider seguía mandando el formato multipart de `flux-2-dev`, que `flux-1-schnell` no acepta (payloads no intercambiables entre modelos).

**Decisión**: se descartó `flux-2-dev` por completo (sin reintentar) y se corrigió el provider para mandar el formato JSON real que `flux-1-schnell` espera (ver contrato arriba) — `_DEFAULT_STEPS` bajado a 4 (default documentado de Cloudflare para este modelo) y `CLOUDFLARE_IMAGE_MODEL` cambiado a `flux-1-schnell` como default en `settings.py`.

**Resultado, con el mismo `req_scene02_v1` reintentado una sola vez tras la corrección**: `HTTP 200`, imagen real decodificada y validada con Pillow (`JPEG`, `1024×1024`, `RGB`), guardada en `lab/workspace/media/793ff158b714/images/generated/scene_02-img_001.jpeg`, registrada en `asset_registry.json` como `asset_id: img_001`, `provider: cloudflare`, `model: @cf/black-forest-labs/flux-1-schnell`, `provenance: AI_GENERATED`, `status: READY` — y el bootstrap de continuidad de personaje funcionó (`img_001` quedó como primera referencia de `jonathan_sia`). **Primer asset real de todo el LAB.**

En los 5 intentos fallidos previos: cero assets corruptos, cero registros parciales — cada fallo quedó como `generation_request.status: FAILED` con su error real, exactamente el comportamiento de manejo de fallos diseñado.

## `requested_aspect_ratio` vs `actual_aspect_ratio` (deuda técnica cerrada)

El asset `img_001` de arriba expuso un problema real: `flux-1-schnell` no acepta ningún parámetro de tamaño y siempre entrega `1024×1024`, sin importar qué `aspect_ratio` pida el `generation_request` (`9:16` en este caso). El `asset_registry.json` tenía un único campo `aspect_ratio` que guardaba lo *pedido*, no lo que el archivo físico realmente era — una afirmación falsa sobre el asset (`img_001` decía `"aspect_ratio": "9:16"` siendo en realidad `1024×1024`, es decir `1:1`).

Corregido reemplazando ese campo por dos, en `asset_registry.json` (esquema completo en `docs/LAB_MEDIA_ASSETS.md`):
- **`requested_aspect_ratio`** — la intención de generación (lo que decía el `generation_request`). `null` si nunca se pidió uno.
- **`actual_aspect_ratio`** — derivado siempre de `width`/`height` reales (`lab/media/registry.py :: _derive_aspect_ratio()`, MCD reducido), nunca del request ni del provider. `null` si no hay dimensiones (nunca se fabrica).

`width`/`height` siguen siendo, como siempre, la medición real del archivo con Pillow — nunca se recortan/redimensionan para "hacer coincidir" con lo pedido; eso es trabajo explícito de una fase posterior, no de Fase 3. El registro de `img_001` se migró al nuevo esquema (`requested_aspect_ratio: "9:16"`, `actual_aspect_ratio: "1:1"`) — sin regenerar el archivo.

## Limitaciones conocidas de FLUX.1 schnell (consolidado)

- Genera siempre `1024×1024` en este flujo — no acepta `width`/`height`/`aspect_ratio` en el request.
- No soporta imagen de entrada en absoluto — sin edición, sin referencias (`edit()`/`generate_from_references()` no son operaciones válidas contra este modelo).
- `steps`: máximo 8, default 4 (documentado oficialmente).
- Formato de salida observado: JPEG (no PNG) — detectado del contenido real, nunca asumido.
