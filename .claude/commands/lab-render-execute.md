---
description: LAB -- ejecuta FFmpeg real sobre render_plan.json (Fase 4.2 etapa 5), produce el primer video real de la historia. Sin costo de API, pero SI crea archivos de video en disco.
---

Renderizá de verdad los shots elegibles de la historia `$ARGUMENTS` (un `story_id` -- debe tener `render_plan.json` de Fase 4.2 etapa 3/4). Si no se pasó, pedíselo al usuario.

**Esta es la primera etapa de LAB que produce video real y escribe archivos en disco.** No llama a ninguna API externa (FFmpeg corre 100% local), pero sí es ejecución real -- avisá al usuario antes de correrlo si no es obvio por contexto que lo está pidiendo a propósito.

Pasos:

1. Si `lab/workspace/media/<story_id>/render_plan.json` no existe todavía, avisar y sugerir `/lab-render-plan <story_id>` primero.

2. Ejecutar:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli render-execute <story_id>
   ```
   Esto procesa los shots elegibles (los que tienen un asset de imagen real y geometría computable-o-nula) -- cada uno corre un comando de FFmpeg real y produce un `.mp4` en `videos/rendered/`. Reescribe `render_plan.json` con el resultado real (`status: DONE/FAILED`, `output_path`/`error`). Los shots sin asset (texto-only) o con geometría no computable quedan `PENDING`, sin tocar -- **no es un error**, es contenido que esta etapa deliberadamente no intenta renderizar (no inventa un tratamiento visual para ellos).

3. Para reintentar/procesar un solo shot:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli render-execute <story_id> --shot-id <render_shot_id>
   ```

4. Reportar al usuario, en texto claro:
   - Cuántos shots quedaron `DONE` (con la ruta del `.mp4`), cuántos `FAILED` (con el error tal cual, sin intentar corregirlo automáticamente), y cuántos `PENDING` (y por qué -- sin asset, o geometría no computable).
   - Que esto es un clip por shot, sin concatenar, sin transiciones, sin audio, sin motion/Ken-Burns -- eso todavía no existe.

**Nunca**: llamar a Gemini/Cloudflare/cualquier VideoProvider, tocar producción, modificar `animation_plan.json`, `sequence.json` o `asset_registry.json`, inventar un render para un shot sin asset real.
