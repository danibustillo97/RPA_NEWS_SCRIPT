---
title: LAB -- Sequence & Animation Engine (Fase 4)
status: Fase 4 implementada (solo planificación, sin render)
date: 2026-09-10
---

# Sequence & Animation Engine

Fase 4 convierte "tengo varias imágenes" en "tengo una secuencia narrativa con orden, duración, movimiento y transiciones" — **sin generar video, sin animar nada todavía**. Consume el `media_blueprint.json` de Fase 3 (qué assets existen) y los artifacts narrativos de Fase 2 (`scene_plan.json`, `script.json`, `editorial_analysis.json`, etc.) para producir `sequence.json`: una representación declarativa y reproducible de cómo esos assets deberían convertirse en una secuencia audiovisual.

## Principio central: declarar, no ejecutar

El Sequence Engine puede decir "usá este asset 3.5 segundos, hacé un slow zoom-in, entrá con fade, salí con cut" — sin ejecutar nada de eso. `motion`/`transition_in`/`transition_out` son etiquetas declarativas; ninguna animación real ocurre en esta fase. Eso es explícitamente trabajo de una fase futura (Animation Engine → Image-to-Video Provider → Renderer).

## Arquitectura

```
Story (Fase 2, artifacts narrativos)          Media Blueprint (Fase 3, assets reales)
   |                                                |
   '------------------------+-----------------------'
                             v
              skill: lab-sequence-planning
        (Content-aware sequencing + duración/framing/
         motion/transition por shot + suggested_transform
         -- un mismo pase de juicio sobre la misma historia)
                             | escribe con Write
                             v
        lab/workspace/media/<story_id>/sequence.json
                             |
                 lab.cli sequence-record <story_id>
        (valida referencias + vocabulario + registra job sequence_plan)
                             v
                    sequence.json validado, status: DRAFT
                             |
                 lab.cli sequence-review <story_id>   (opcional, a pedido del usuario)
                             v
                       status: READY_FOR_REVIEW
                             |
                    revisión humana manual (igual que el resto de LAB)
                             v
                   Fase 5 (Animation Engine, todavía no implementada)
```

`lab/sequence/` (Python, ejecución determinística) es la contraparte de la skill: `planner.py` valida referencias reales (`scene_id` contra `media_blueprint.json`, `asset_id` contra `asset_registry.json`) y deriva `transform_required` de dimensiones reales — nunca decide narrativa ni el tipo de transformación, eso es criterio de la skill.

## Por qué un artifact separado (`sequence.json`), no un campo dentro de `media_blueprint.json`

La documentación de Fase 3 originalmente anticipaba que Fase 4 agregaría una clave `sequence` a cada entrada de `media_blueprint.json :: scenes[]`. Con el diseño real de Fase 4 en mano, eso cambió: una secuencia ordena **shots** a través de toda la historia, y un shot no tiene por qué corresponder 1:1 con una escena (una escena puede aportar 0, 1 o varios shots; el orden final de shots no tiene por qué calcar el orden de `scene_plan.json`). Anidar eso dentro de `scenes[]` obligaría a forzar una correspondencia que no siempre existe. `sequence.json`, con `shots[]` como lista plana top-level, refleja mejor qué es realmente una secuencia. `media_blueprint.json` no se modificó.

## Modelo de `sequence.json`

```json
{
  "sequence_id": "seq_001",
  "story_id": "793ff158b714",
  "target_format": "REEL",
  "target_aspect_ratio": "9:16",
  "narrative_structure": "HOOK -> ESTABLISHING -> CHARACTER_INTRO -> EMOTIONAL_BEAT -> CLOSING",
  "status": "DRAFT",
  "shots": [
    {
      "shot_id": "shot_01",
      "scene_id": "scene_01",
      "asset_id": null,
      "order": 1,
      "duration_seconds": 3.0,
      "framing": "primer plano en manos, texto superpuesto",
      "motion": "STATIC",
      "transition_in": "NONE",
      "transition_out": "CUT",
      "purpose": "hook",
      "notes": "escena TEXT_ONLY de Fase 2 -- sin asset generado",
      "transform_required": null,
      "suggested_transform": null
    },
    {
      "shot_id": "shot_02",
      "scene_id": "scene_02",
      "asset_id": "img_001",
      "order": 2,
      "duration_seconds": 4.0,
      "framing": "plano medio, silueta a contraluz",
      "motion": "SLOW_ZOOM_IN",
      "transition_in": "FADE",
      "transition_out": "CUT",
      "purpose": "character_intro",
      "notes": "",
      "transform_required": true,
      "suggested_transform": "EXTEND"
    }
  ],
  "total_duration_seconds": 7.0,
  "created_at": "2026-09-10T..."
}
```

### `target_aspect_ratio` (secuencia) vs `actual_aspect_ratio` (asset) — misma disciplina que Fase 3

Un asset puede ser `actual_aspect_ratio: "1:1"` (medido de verdad, ver `docs/LAB_MEDIA_ASSETS.md`) mientras la secuencia entera necesita `target_aspect_ratio: "9:16"`. El shot **no vuelve a copiar** el aspect ratio del asset (eso ya vive en `asset_registry.json`, por `asset_id` — duplicarlo reintroduciría el mismo riesgo de desincronización que la corrección `requested_aspect_ratio`/`actual_aspect_ratio` de Fase 3 acaba de cerrar). En su lugar:

- **`transform_required`** (booleano): `lab.sequence.planner.derive_transform_requirement()` lo deriva siempre comparando el `actual_aspect_ratio` real del asset (leído del registry) contra el `target_aspect_ratio` de la secuencia — nunca a mano, nunca del request. `null` si el shot no tiene `asset_id`.
- **`suggested_transform`** (`CROP`/`FIT`/`EXTEND`/`COMPOSE`/`UNKNOWN`): criterio de la skill, solo cuando `transform_required: true`. Nada se ejecuta — la transformación real (crop/fit/extend/compose) es responsabilidad explícita de una fase posterior de composición/render.

El asset original **nunca se modifica** por esto — ni el archivo, ni `width`/`height` en el registry.

### Campos del shot (mínimo)

`shot_id`, `scene_id` (trazable a `scene_plan.json`/`media_blueprint.json`), `asset_id` (opcional — `null` para shots `TEXT_ONLY`/`NO_MEDIA`, trazable a `asset_registry.json` cuando existe), `order` (1..N sin huecos ni repetidos), `duration_seconds`, `framing` (texto libre), `motion`, `transition_in`/`transition_out`, `purpose`, `notes`, `transform_required`, `suggested_transform`.

`motion`: `STATIC` / `SLOW_ZOOM_IN` / `SLOW_ZOOM_OUT` / `PAN_LEFT` / `PAN_RIGHT` / `PAN_UP` / `PAN_DOWN` / `PUSH_IN` / `PULL_OUT`.

`transition_in`/`transition_out`: `NONE` / `CUT` / `FADE` / `DISSOLVE` — vocabulario propio de LAB (el brief de Fase 4 solo daba `FADE`/`CUT` como ejemplos); extensible sin romper el esquema.

## Content-aware sequencing

El orden de los shots no es solo "un shot por escena en orden" — la skill usa la narrativa ya decidida en Fase 2 (`editorial_analysis.json :: angle`/`narrative_strength`, `script.json` si existe, `hooks.json` si existe) para decidir la estructura. Referencia (no regla rígida, extensible): hook → establishing shot → presentación del personaje → contexto → conflicto → beat emocional → resolución/CTA. Una historia sin conflicto marcado o sin CTA es válida y no fuerza esos beats — igual que en Fase 2, forzar una estructura donde no corresponde sería peor que no tenerla.

## Trazabilidad y no-duplicación

`story → scene → asset → shot` es trazable por ID en cada dirección: cada shot referencia `scene_id` (real, en `media_blueprint.json`) y opcionalmente `asset_id` (real, en `asset_registry.json`) — nunca se copian. `lab.cli sequence-record` valida ambas referencias antes de aceptar la secuencia como válida; si algo no existe, el error lo dice explícitamente. Ningún asset nuevo se crea por aparecer en una secuencia — `lab/media/registry.py` no se toca desde `lab/sequence/`.

## Human Review

`sequence.json :: status` usa el mismo vocabulario conceptual que `WorkflowState` (`DRAFT` ~ `PROCESSING`, `READY_FOR_REVIEW`, `APPROVED`, `REJECTED`) pero es su propio campo — no es el `WorkflowState` del `WorkspaceItem` (que sigue en `READY_FOR_REVIEW` desde Fase 2/3, sin cambios; `lab/core/workspace.py` no se tocó). `lab.cli sequence-review` lleva `DRAFT → READY_FOR_REVIEW` (validando que la secuencia sea completa y consistente primero). **No existe un comando `sequence-approve`/`sequence-reject`** — confirmado por inspección: LAB no tiene, en ningún punto del sistema (ni para items, ni para assets, ni ahora para secuencias), un mecanismo de aprobación automatizado. La aprobación es manual, fuera de LAB, igual que siempre. No hay ningún camino automático hacia producción.

## Jobs

`sequence_plan` se registra vía `record_job()` (es razonamiento de Claude, como `media_plan` de Fase 3) — un job por corrida de `lab.cli sequence-record`. Ver `docs/LAB_JOBS.md`.

## Fuera de alcance de esta etapa

Generación de video, image-to-video, video-to-video, TTS, clonación de voz, música, render con FFmpeg, subtítulos renderizados, publicación automática, Production News, Supabase, Vercel, cloud storage, import automático a producción. `sequence.json` deja declarado lo necesario para que una fase futura (Animation Engine → Renderer) lo consuma sin tener que reinterpretar la historia desde cero — pero esa fase todavía no existe.

## Limitaciones conocidas de esta primera etapa

- **Sin versionado de secuencias**: replanificar sobreescribe `sequence.json` (igual que `media_plan.json`/`media_blueprint.json` en Fase 3 hoy). Si hace falta conservar versiones anteriores, se agrega como extensión aditiva más adelante.
- **`suggested_transform` es juicio editorial**, no una fórmula: Python valida vocabulario y consistencia (`transform_required` ↔ `suggested_transform` no nulo), nunca "corrección" — eso es revisión humana.
- **Cobertura de datos reales limitada** (al momento de esta implementación): la única historia real con al menos un asset generado es `793ff158b714` (1 asset real, `img_001`, más escenas `TEXT_ONLY` sin asset) — no hay todavía un caso real con múltiples assets por escena ni con `EDITED_IMAGE`.
