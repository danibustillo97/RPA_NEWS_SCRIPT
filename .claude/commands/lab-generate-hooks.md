---
description: LAB -- genera hooks (parte de la skill lab-editorial-narrative) para un item con historia narrable
---

Corre la parte de hooks de la skill lab-editorial-narrative sobre el item `$ARGUMENTS`. Si no se paso un item_id, pediselo al usuario.

Requiere content_plan.json ya escrito (producido por lab-editorial-storycraft / /lab-find-stories). Si content_plan.json :: narrative_recommended es false, avisa al usuario que este item no fue recomendado para formato narrativo y pregunta si quiere generar hooks de todas formas antes de proceder -- no lo hagas por defecto.

Produce hooks.json. Reporta cuantos hooks se generaron y de que hecho/angulo sale cada uno (based_on).
