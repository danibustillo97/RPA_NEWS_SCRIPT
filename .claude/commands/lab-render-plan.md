---
description: LAB -- genera/actualiza render_plan.json desde animation_plan.json (Fase 4.2 etapa 4), sin ejecutar FFmpeg ni llamar ningun provider
---

Corre la skill `lab-render-planning` sobre la historia `$ARGUMENTS` (un `story_id` -- debe tener `animation_plan.json` de Fase 4.2 etapa 1/2). Si no se pasó, pedíselo al usuario.

Pasos:

1. Confirmar que existe `lab/workspace/media/<story_id>/animation_plan.json`. Si no existe, avisar y sugerir `/lab-animation-plan <story_id>` primero.

2. Ejecutar:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli render-plan <story_id>
   ```
   Esto genera/actualiza `render_plan.json` (vía `lab.render.planner.init_render_plan()`, sin decidir nada nuevo -- toda la lógica ya existe en `lab/render/`), corre `validate_render_plan()`, y registra el job `render_plan`.

3. Reportar al usuario, en texto claro:
   - `story_id`, `animation_plan_id`, `target_aspect_ratio`, `target_width`/`target_height`.
   - Por cada shot: `backend`, y `transform_geometry` cuando exista (computable o no -- nunca inventado, solo si el animation plan ya declaraba `source_transform.required: true` para ese shot).
   - Errores de validación si los hay -- mostrarlos tal cual, sin intentar corregirlos sin que el usuario lo pida.
   - Que el plan quedó en `DRAFT`, sin ninguna aprobación automática.

**Nunca**: generar video, ejecutar FFmpeg real, llamar a Gemini/Cloudflare/cualquier VideoProvider, tocar producción, modificar `animation_plan.json`, `sequence.json` o `asset_registry.json`.
