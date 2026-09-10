---
description: LAB -- planifica que media necesita una historia (skill lab-media-planning), sin generar nada todavia
---

Corre la skill `lab-media-planning` sobre la historia `$ARGUMENTS` (un `story_id` -- el `item_id` de una noticia ya en `READY_FOR_REVIEW` con `scene_plan.json` de Fase 2). Si no se pasó un `story_id`, pedíselo al usuario.

Esto produce `visual_style.json`, `character_profiles/*.json`, `media_plan.json`, `generation_requests.json` y `media_blueprint.json` en `lab/workspace/media/<story_id>/` -- **sin llamar a Gemini ni gastar nada todavía**. Es el paso de control de costos: mostrar qué se necesita antes de generar.

Reportá al usuario, en texto claro:
- Cuántas escenas hay y cuántas de cada `media_type`.
- Cuántas requieren generación real y con qué proveedor.
- Si alguna escena cambió de tipo respecto al `scene_plan.json` original de Fase 2 (ej. `REAL_IMAGE` reclasificado a `GENERATED_IMAGE` porque no hay foto real disponible) -- explicá el motivo, es una decisión esperada del Decision Engine, no un error.
- Que el plan quedó guardado y listo para `/lab-generate-media` cuando el usuario decida seguir.
