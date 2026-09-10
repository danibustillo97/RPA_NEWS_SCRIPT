---
description: LAB -- muestra el estado de la secuencia (sequence.json) de una historia
---

Ejecutá:
```
lab/.venv/Scripts/python.exe -m lab.cli sequence-status <story_id>
```
(`story_id` viene de `$ARGUMENTS`; pedíselo al usuario si no lo pasó.)

Reportá en una línea o lista corta: estado de la secuencia (`DRAFT`/`READY_FOR_REVIEW`/`APPROVED`/`REJECTED`), formato y aspect ratio objetivo, cuántos shots hay, cuántos usan asset vs son solo texto, cuántos necesitan transformación, y la duración total. Si no hay ninguna secuencia todavía para esa historia, decíselo directo y sugerí `/lab-sequence-plan`.
