---
description: LAB -- corre el análisis editorial y descubrimiento de historia (skill lab-editorial-storycraft) sobre un item ya entendido
---

Corré la skill `lab-editorial-storycraft` sobre el item `$ARGUMENTS`. Si no se pasó un `item_id`, pedíselo al usuario.

Requiere que `understanding.json` ya exista para ese item (producido por `lab-editorial-understanding` / `/lab-analyze-news`). Si no existe, avisá al usuario y sugerí correr `/lab-analyze-news <item_id>` primero -- no intentes generar el análisis editorial sin el entendimiento factual de base.

Esto produce `editorial_analysis.json`, `story_concepts.json` y `content_plan.json`. Reportá al usuario el ángulo encontrado (o la ausencia explícita de uno -- "no hay historia suficientemente fuerte" es un resultado válido, no lo presentes como un problema) y el formato recomendado.
