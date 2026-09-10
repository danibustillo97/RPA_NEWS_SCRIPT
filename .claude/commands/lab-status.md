---
description: LAB — muestra cuántos items hay en cada estado del workspace
---

Ejecutá en la raíz del repo (`RPA_NEWS_SCRIPT/`):
```
lab/.venv/Scripts/python.exe -m lab.cli status
```

Reportale al usuario, en una línea o una lista corta, cuántos items hay en cada estado (`INGESTED`, `PROCESSING`, `READY_FOR_REVIEW`, `APPROVED`, `REJECTED`). Si todo está en cero, decilo directamente — no hace falta narrar cada carpeta vacía.
