---
description: LAB -- genera/actualiza animation_plan.json desde sequence.json (Fase 4.2 etapa 2), sin generar video ni llamar ningun provider
---

Corre la skill `lab-animation-planning` sobre la historia `$ARGUMENTS` (un `story_id` -- debe tener `sequence.json` de Fase 4.1). Si no se pasó, pedíselo al usuario.

Pasos:

1. Confirmar que existe `lab/workspace/media/<story_id>/sequence.json`. Si no existe, avisar y sugerir `/lab-sequence-plan <story_id>` primero.

2. Ejecutar:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli animation-plan <story_id>
   ```
   Esto genera/actualiza `animation_plan.json` (vía `lab.animation.planner.init_animation_plan()`, sin decidir nada nuevo -- toda la lógica ya existe en `lab/animation/`), corre `validate_animation_plan()`, y registra el job `animation_plan`.

3. Reportar al usuario, en texto claro:
   - `story_id`, `sequence_id`, cantidad de shots, duración total.
   - Por cada shot: `strategy`/`backend`/`motion`, y `source_transform` cuando exista (nunca inventado -- solo si `sequence.json` ya declaraba `transform_required: true` para ese shot).
   - Errores de validación si los hay -- mostrarlos tal cual, sin intentar corregirlos sin que el usuario lo pida.
   - Que el plan quedó en `DRAFT`, sin ninguna aprobación automática.

**Nunca**: generar video, llamar a Gemini/Cloudflare/cualquier VideoProvider, introducir FFmpeg real, tocar producción, modificar `sequence.json` o `asset_registry.json`.
