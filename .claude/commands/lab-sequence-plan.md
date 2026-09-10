---
description: LAB -- planifica la secuencia declarativa (orden, duracion, movimiento, transiciones) de una historia, sin generar video
---

Corre la skill `lab-sequence-planning` sobre la historia `$ARGUMENTS` (un `story_id` -- debe tener `media_blueprint.json` de Fase 3 y `scene_plan.json` de Fase 2). Si no se pasó un `story_id`, pedíselo al usuario.

Esto produce `lab/workspace/media/<story_id>/sequence.json` -- una lista de shots con orden, duración, encuadre, movimiento y transiciones, y (cuando un asset no coincide con el aspect ratio objetivo) la necesidad de transformación declarada. **No genera ni anima nada** — es solo el plan.

Reportá al usuario, en texto claro:
- Cuántos shots tiene la secuencia y cuántos usan un asset real vs son solo texto.
- Cuántos shots necesitan `suggested_transform` (y de qué tipo) porque el asset no coincide con el aspect ratio objetivo de la secuencia — explicá que nada se recorta/redimensiona todavía, solo queda declarado.
- Duración total.
- Que la secuencia quedó en `DRAFT`, lista para que el usuario la revise o pida `/lab-sequence-status` más tarde.
