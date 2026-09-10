---
name: lab-editorial-understanding
description: This skill should be used when the user asks to "understand a news item", "analiza esta noticia", "entiende esta noticia", "investiga contexto de esta noticia", "verifica los hechos de esta noticia", or runs `/lab-analyze-news <item_id>` / the first stage of `/lab-process-news <item_id>` in the LAB local editorial lab (RPA_NEWS_SCRIPT repo). Produces understanding.json, research.json, and fact_check.json for a LAB item.
---

Produce el entendimiento factual base de un item de LAB: que paso, que contexto falta, y que tan verificable es cada afirmacion. Es el primer cluster del pipeline editorial de Fase 2 (docs/LAB_EDITORIAL_INTELLIGENCE.md) -- todo lo que produzcan lab-editorial-storycraft y lab-editorial-narrative depende de esto, asi que la precision aca importa mas que la velocidad.

## Regla NO INVENTAR (obligatoria en todo el output)

Cada hecho, numero o afirmacion lleva una etiqueta de procedencia: SOURCE_FACT (literal de la noticia), VERIFIED_CONTEXT (confirmado con fuente externa citada), INFERENCE (conclusion razonada), UNVERIFIED (no se pudo confirmar -- declararlo, no inventarlo). Esquema completo: docs/LAB_ARTIFACTS.md.

## Pasos

1. Si el item todavia esta en INGESTED, arrancar el pipeline:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli editorial-start <item_id>
   ```
   Esto devuelve item_dir (la carpeta donde van los artifacts, lab/workspace/processing/<item_id>/). Si el item ya esta en PROCESSING (por ejemplo, corriendo esta skill sola despues de otra etapa), leer item.json ahi directamente en vez de volver a arrancar.

2. Leer item.json en item_dir -- title, content, source, source_url, published_at son la materia prima.

3. Escribir understanding.json en item_dir (esquema completo en docs/LAB_ARTIFACTS.md): headline, que paso, 5W+H, key_facts con su provenance, entidades, numeros importantes con contexto, y -- campos obligatorios, no opcionales -- uncertainty y missing_information: que no queda claro o no dice la fuente. Todo lo que venga literal del content es SOURCE_FACT.

4. Identificar que preguntas de contexto haria falta responder para entender mejor la noticia (ej. "es la primera vez que pasa esto?", "que dice la ley al respecto?"). Para cada una:
   - Si amerita, usar WebSearch/WebFetch para buscar una fuente publica confiable. Si se encuentra, la respuesta va con status: VERIFIED_CONTEXT, answer y source_url de esa fuente -- nunca mezclada con los hechos de understanding.json.
   - Si no se encuentra nada confiable, o la pregunta no amerita buscar, queda status: NEEDS_RESEARCH con answer: null -- es un resultado valido, no forzar una respuesta.
   Escribir todo en research.json (context_needs[] + related_questions[]).

5. Listar las afirmaciones importantes de la noticia (no triviales, las que sostienen la historia) y clasificar cada una en fact_check.json: VERIFIED (confirmada con fuente propia), SOURCE_ONLY (solo la dice la fuente original, sin verificacion independiente -- el caso mas comun), UNVERIFIED, CONTRADICTED, o NEEDS_RESEARCH.

6. Registrar la etapa:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli editorial-stage-done <item_id> UNDERSTANDING
   ```
   Este comando falla si ninguno de los 3 artifacts existe todavia -- escribirlos antes de correrlo.

7. Reportar al usuario, en texto claro: el resumen de que paso, cuantos context_needs quedaron NEEDS_RESEARCH vs VERIFIED_CONTEXT, y si algo relevante quedo UNVERIFIED o CONTRADICTED en el fact-check -- eso es informacion editorial importante, no ruido.

## Cuando se detiene esta skill sola

Si /lab-analyze-news la invoco sola (no como parte de /lab-process-news), termina aca -- no sigue automaticamente a lab-editorial-storycraft. El item queda en PROCESSING con estos 3 artifacts, listo para que /lab-find-stories continue cuando el usuario lo pida.
