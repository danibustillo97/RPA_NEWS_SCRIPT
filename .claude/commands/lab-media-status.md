---
description: LAB -- muestra el estado de generacion de media de una historia (requests y assets)
---

Ejecutá:
```
lab/.venv/Scripts/python.exe -m lab.cli media-status <story_id>
```
(`story_id` viene de `$ARGUMENTS`; pedíselo al usuario si no lo pasó.)

Reportá en una línea o lista corta: cuántos `generation_requests` hay por estado (`PENDING`/`DONE`/`FAILED`), cuántos assets hay en total y por estado (`READY`/`REJECTED`/`REGENERATE`/`FAILED`), y el estado del `media_blueprint` (`PLANNED`/`GENERATING`/etc). Si no hay ningún plan todavía para esa historia, decíselo directo y sugerí `/lab-media-plan`.
