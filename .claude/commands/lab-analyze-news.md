---
description: LAB -- corre solo el entendimiento factual (skill lab-editorial-understanding) sobre un item
---

Corré la skill `lab-editorial-understanding` sobre el item `$ARGUMENTS`. Si no se pasó un `item_id`, pedíselo al usuario.

Esto produce `understanding.json`, `research.json` y `fact_check.json` (ver `docs/LAB_ARTIFACTS.md`) y deja el item en `PROCESSING` -- no sigue automáticamente al análisis editorial (`lab-editorial-storycraft`); eso se hace con `/lab-find-stories` cuando el usuario lo pida, o con `/lab-process-news` si quiere el pipeline completo de una.

Reportá al usuario el resumen factual y qué preguntas de contexto quedaron sin resolver (`NEEDS_RESEARCH` en `research.json`).
