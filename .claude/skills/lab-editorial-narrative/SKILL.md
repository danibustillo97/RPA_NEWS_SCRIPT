---
name: lab-editorial-narrative
description: This skill should be used when the user asks to "generate hooks for this news item", "genera hooks", "escribe el guion", "crea el scene plan", "create a script", or runs `/lab-generate-hooks <item_id>` / `/lab-create-script <item_id>` / the third stage of `/lab-process-news <item_id>` in the LAB local editorial lab (RPA_NEWS_SCRIPT repo). Produces hooks.json, script.json, and scene_plan.json for a LAB item — only when content_plan.json recommends a narrative format.
---

Convierte un ángulo/historia ya validado (por lab-editorial-storycraft) en hooks, guion y plan de escenas concretos. Es el tercer cluster del pipeline editorial de Fase 2 (docs/LAB_EDITORIAL_INTELLIGENCE.md) -- solo debe correr si content_plan.json :: narrative_recommended es true.

## Guardia obligatoria: no forzar contenido narrativo

Antes de escribir cualquier artifact, leer content_plan.json en item_dir. Si narrative_recommended es false, no generar hooks/guion/escenas -- avisar al usuario que el content_plan no recomendo formato narrativo para este item y detenerse ahi (el item sigue su camino a READY_FOR_REVIEW igual, solo que sin estos 3 artifacts). Si el usuario insiste explicitamente en generarlos de todas formas, confirmar antes de proceder y dejar constancia en el reasoning de que fue un pedido explicito contra la recomendacion.

## Pasos (cuando narrative_recommended: true)

1. Confirmar los artifacts previos con:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli editorial-show <item_id>
   ```
   Leer understanding.json (hechos), editorial_analysis.json (angulo) y story_concepts.json (conceptos de historia) -- el material narrativo sale de ahi, no de reinterpretar la noticia desde cero.

2. Escribir hooks.json (esquema en docs/LAB_ARTIFACTS.md): 2-4 hooks, cada uno con su strategy y based_on apuntando al hecho o angulo concreto del que sale -- nunca un hook sin apoyo trazable en los artifacts anteriores. provenance: CREATIVE_FRAMING (es una decision de formato, no un hecho nuevo).

3. Escribir script.json: secciones HOOK/SETUP/CONTEXT/DEVELOPMENT/TURNING_POINT/PAYOFF/CLOSING -- no todas son obligatorias en cada guion, usar las que la historia sostenga. Cualquier hecho citado en el guion lleva su provenance real (SOURCE_FACT/VERIFIED_CONTEXT), no CREATIVE_FRAMING -- solo la eleccion de como contarlo es CREATIVE_FRAMING.

4. Escribir scene_plan.json: una escena por beat narrativo relevante, con visual_description y required_media_type (REAL_IMAGE/GENERATED_IMAGE/EDITED_IMAGE/NO_IMAGE). Esta skill decide que tipo de media hace falta -- no genera ni edita ninguna imagen; eso es el Media Agent (Fase 3, todavia no implementado).

5. Registrar la etapa:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli editorial-stage-done <item_id> NARRATIVE
   ```

6. Reportar al usuario: cuantos hooks se generaron, la estructura del guion en una linea por seccion, y cuantas escenas necesitan REAL_IMAGE vs GENERATED_IMAGE vs NO_IMAGE (eso anticipa el trabajo de Fase 3 sin implementarlo).

## Cierre del pipeline

Despues de esta etapa (o de que se decida no correrla), el flujo completo pasa a READY_FOR_REVIEW con:
```
lab/.venv/Scripts/python.exe -m lab.cli editorial-review <item_id>
```
Esto lo hace /lab-process-news automaticamente al final; si esta skill corrio sola via /lab-generate-hooks o /lab-create-script, avisar al usuario que el item sigue en PROCESSING hasta que se corra editorial-review explicitamente (o el resto del pipeline).
