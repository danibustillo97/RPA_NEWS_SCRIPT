---
description: LAB -- corre el pipeline editorial completo (understanding -> storycraft -> narrative si aplica) sobre un item y lo deja en READY_FOR_REVIEW
---

Vas a correr el pipeline editorial de Fase 2 completo sobre el item `$ARGUMENTS` (ver `docs/LAB_EDITORIAL_INTELLIGENCE.md`). Si no se pasó un `item_id`, pedíselo al usuario o listá los items en `INGESTED` con `lab/.venv/Scripts/python.exe -m lab.cli status` para que elija.

Pasos:

1. Correr la skill `lab-editorial-understanding` sobre el item (arranca el pipeline si está en `INGESTED`, produce `understanding.json`/`research.json`/`fact_check.json`, registra la etapa `UNDERSTANDING`).

2. Correr la skill `lab-editorial-storycraft` (produce `editorial_analysis.json`/`story_concepts.json`/`content_plan.json`, registra `STORYCRAFT`).

3. Leer `content_plan.json` recién escrito. Si `narrative_recommended` es `true`, correr la skill `lab-editorial-narrative` (produce `hooks.json`/`script.json`/`scene_plan.json`, registra `NARRATIVE`). Si es `false`, **no correrla** -- es un resultado válido, no un paso saltado por error.

4. Cerrar el pipeline:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli editorial-review <item_id>
   ```

5. Reportar al usuario, en texto claro (no JSON crudo salvo que lo pida):
   - Resumen de qué entendió (headline, ángulo encontrado o su ausencia).
   - Si se generó contenido narrativo o no, y por qué.
   - Que el item quedó en `READY_FOR_REVIEW` (`lab/workspace/review/<item_id>/`) esperando revisión humana -- ningún paso de este comando aprueba, exporta ni publica nada.

Si cualquier paso falla (el CLI devuelve `{"error": ...}` o una excepción), detenerse ahí, mostrar el error tal cual, y no intentar forzar el siguiente paso ni improvisar una corrección automática.
