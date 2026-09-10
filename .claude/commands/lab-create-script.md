---
description: LAB -- genera guion y plan de escenas (parte de la skill lab-editorial-narrative) para un item con historia narrable
---

Corre la parte de guion + scene plan de la skill lab-editorial-narrative sobre el item `$ARGUMENTS`. Si no se paso un item_id, pediselo al usuario.

Requiere content_plan.json ya escrito (producido por lab-editorial-storycraft / /lab-find-stories). Si content_plan.json :: narrative_recommended es false, avisa al usuario y confirma antes de proceder -- no lo hagas por defecto.

Produce script.json y scene_plan.json. Reporta la estructura del guion (una linea por seccion) y cuantas escenas necesitan REAL_IMAGE vs GENERATED_IMAGE vs NO_IMAGE.
