---
description: LAB -- genera de verdad los assets de media de una historia con Gemini (llama a la API real, tiene costo)
---

Generá los assets de media reales para la historia `$ARGUMENTS` (un `story_id`). Si no se pasó, pedíselo al usuario.

Pasos:

1. Si `lab/workspace/media/<story_id>/media_plan.json` no existe todavía, correr primero la skill `lab-media-planning` (mismo procedimiento que `/lab-media-plan`) para producirlo.

2. Antes de generar nada, confirmá que `GEMINI_API_KEY` está configurada (`lab/config/.env`) -- si `lab.cli media-generate` falla con un error de credencial, mostrá el error tal cual y no intentes ningún workaround; la key es responsabilidad del usuario (ver `docs/LAB_SECURITY.md`).

3. Ejecutar:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli media-generate <story_id>
   ```
   Esto procesa todos los `generation_requests` en `PENDING` -- cada uno es una llamada real y paga a Gemini. **No lo corras sin que el usuario haya visto primero el resumen de `/lab-media-plan`** (a menos que ya lo haya corrido en este mismo pedido).

4. Reportar, por escena: si se generó el asset, dónde quedó guardado (`relative_path`), y si algún request falló (`status: FAILED`) -- mostrá el error tal cual, sin reintentar automáticamente.

5. Si el usuario pide reintentar un request fallido:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli media-generate <story_id> --retry <request_id>
   ```

6. Cerrar recordando que la historia sigue en `READY_FOR_REVIEW` (Fase 3 no la mueve a `APPROVED`) -- el humano revisa las imágenes, el prompt, la procedencia y la consistencia visual antes de aprobar cualquier asset (ver `docs/LAB_MEDIA_ASSETS.md`, sección Human Review).
