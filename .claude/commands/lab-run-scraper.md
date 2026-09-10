---
description: LAB — corre la ingestión local (job run_scraper) y reporta el resultado
---

Vas a correr el job `run_scraper` de LAB — la capacidad de ingestión local (ver `docs/LAB_ARCHITECTURE_AUDIT.md` sección N y `docs/LAB_JOBS.md`). Esto visita las fuentes de noticias, extrae candidatos reales, aplica los gates de calidad y guarda lo que pasa en `lab/workspace/incoming/` como items en estado `INGESTED`. No escribe a Supabase, no toca producción, no decide nada editorial.

Pasos:

1. Ejecutá en la raíz del repo (`RPA_NEWS_SCRIPT/`):
   ```
   lab/.venv/Scripts/python.exe -m lab.cli run-scraper $ARGUMENTS
   ```
   Si el usuario no pasó argumentos, corré sin flags (usa todas las fuentes, tope 30 items). Si pidió una prueba rápida, sugerí `--max-sources 5 --max-items 5`.

2. El comando imprime el job completo en JSON (`status`, `result` con `sources_visited/candidates_found/saved/skipped_duplicate/skipped_quality/errors`, o `error` si falló).

3. Reportale al usuario, en texto claro (no pegues el JSON crudo salvo que lo pida):
   - Cuántas fuentes se visitaron y cuántos items nuevos quedaron en `INGESTED`.
   - Cuántos se saltearon por duplicado o por no pasar el gate de calidad.
   - Si hubo errores, cuáles y en qué fuente.
   - Que los items quedan en `lab/workspace/incoming/` esperando el siguiente paso (procesamiento editorial — todavía no implementado, Fase 2).

4. Si el job falla (`status: failed`), mostrá el campo `error` y no intentes corregir nada automáticamente — es infraestructura local, cualquier fix real se decide con el usuario.

No ejecutes `main.py` (el scraper de producción) bajo ninguna circunstancia desde este comando — son cosas separadas a propósito (ver sección N.3 del audit).
