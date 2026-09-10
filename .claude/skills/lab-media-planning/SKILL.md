---
name: lab-media-planning
description: This skill should be used when the user asks to "plan the media for this story", "planifica el media de esta historia", "decide que imagenes necesita esta historia", "genera el media plan", or runs `/lab-media-plan <story_id>` / the planning stage of `/lab-generate-media <story_id>` in the LAB local editorial lab (RPA_NEWS_SCRIPT repo). Analyzes a story's scene_plan and produces visual_style.json, character_profiles/*.json, media_plan.json, generation_requests.json, and media_blueprint.json — deciding what visual media each scene actually needs, never generating images itself.
---

Decide, escena por escena, que necesita una historia visualmente -- y como pedirlo -- sin generar nada todavia. Es la unica skill de criterio de Fase 3 (Media Intelligence, ver docs/LAB_MEDIA_INTELLIGENCE.md): analisis de media, motor de decision, referencias, continuidad de personajes, identidad visual y prompt engineering son un mismo pase de juicio sobre la misma historia -- no llama a Gemini ni escribe archivos de imagen, eso lo hace lab/media/generation.py despues, en un paso aparte y determinístico.

## Principio central: NO generar una imagen por escena automaticamente

Primero decidir que necesita la escena. No todas las escenas necesitan imagen. No toda imagen debe ser generada -- si el scene_plan de Fase 2 marco una escena como REAL_IMAGE, verificar si de verdad existe una foto real utilizable (ver paso 3) antes de aceptar esa etiqueta; si no existe, corregirla con criterio propio y dejar constancia de por que.

## Pasos

1. Confirmar que la historia esta lista: `story_id` debe tener `scene_plan.json` en `lab/workspace/review/<story_id>/` (Fase 2 completa). Si no existe, avisar al usuario y detenerse -- no inventar escenas.

2. Inicializar el espacio de media:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli media-init <story_id>
   ```
   Devuelve la carpeta (`lab/workspace/media/<story_id>/`) donde escribir todo lo de este paso.

3. Leer `scene_plan.json`, `script.json`, `editorial_analysis.json`, `content_plan.json` y `understanding.json` de `lab/workspace/review/<story_id>/` -- la materia prima real, nunca inventada.

4. **Visual Style** (una sola vez por historia): si `metadata/visual_style.json` no existe todavia, decidir la identidad visual de la historia completa (tono, iluminación, lenguaje de color, lenguaje de cámara, textura, época, nivel de realismo) y escribirlo. Si ya existe (corrida anterior, retry), leerlo y reusarlo tal cual -- no regenerar la identidad visual sin que el usuario lo pida explícitamente. Esquema completo: `docs/LAB_MEDIA_ASSETS.md`.

5. **Character Profiles**: por cada personaje real que aparezca en el script/escenas, si `metadata/character_profiles/<character_id>.json` no existe, crearlo con lo que la fuente realmente sostiene (`understanding.json`/`research.json` de Fase 2) -- `physical_description`/`wardrobe` quedan explícitamente vacíos o `UNVERIFIED` si la fuente no los da, nunca inventados. Si el personaje es una persona privada real sin foto disponible con derechos claros (caso típico: protagonistas de noticias de interés humano), anotarlo en `visual_notes`: no generar una probable semejanza a la persona real, usar una representación genérica. Esta nota es la que después justifica anular un `REAL_IMAGE`.

6. **Media Analysis + Decision Engine, por escena**: para cada escena de `scene_plan.json`, construir un `media_requirement` (esquema en `docs/LAB_MEDIA_ASSETS.md`) con `narrative_purpose`, `visual_purpose`, `subject`, `characters`, `location`, `time_period`, `action`, `emotion`, `composition`, `camera_concept`, `lighting`, `aspect_ratio`, `estimated_duration`, y decidir `media_type` con criterio propio (`REAL_IMAGE`/`GENERATED_IMAGE`/`EDITED_IMAGE`/`ARCHIVE_MEDIA`/`VIDEO`/`GENERATED_VIDEO`/`AUDIO`/`GRAPHIC`/`TEXT_ONLY`/`NO_MEDIA`):
   - `REAL_IMAGE` solo si existe de verdad una foto real utilizable y con derechos claros (rara vez cierto en este pipeline hoy — LAB no busca fotos externas automáticamente, ver `docs/LAB_MEDIA_INTELLIGENCE.md`). Si el `scene_plan.json` de Fase 2 la marcó `REAL_IMAGE` pero no hay tal foto disponible, reclasificar (típicamente a `GENERATED_IMAGE` ilustrativo/genérico) y escribir `decision_reasoning` + `scene_plan_type_override` explicando el cambio — esto es una decisión esperada, no un error.
   - `GENERATED_IMAGE` cuando el momento no tiene material real disponible pero sí vale la pena representarlo visualmente.
   - `EDITED_IMAGE` cuando conviene partir de un asset ya generado (propio u otra escena) y transformarlo (otro aspect ratio, otro encuadre, otra iluminación) en vez de generar desde cero.
   - `TEXT_ONLY`/`NO_MEDIA` cuando la narración funciona sin visual (ver `scene_plan.json` original: las escenas de solo texto de Fase 2 suelen mapear directo acá).
   - `ARCHIVE_MEDIA`/`VIDEO`/`GENERATED_VIDEO`/`AUDIO`/`GRAPHIC` son parte del vocabulario y se pueden asignar si son la decisión correcta, aunque hoy LAB no tiene proveedor que los ejecute (queda como necesidad identificada, no bloquea el resto del plan — ver `docs/LAB_MEDIA_INTELLIGENCE.md` sección de alcance).
   Escribir todos los `media_requirement` en `media_plan.json`.

7. **Prompt Engineering + Referencias**, solo para escenas con `media_type` en `GENERATED_IMAGE`/`EDITED_IMAGE`: construir un `generation_request` por escena con los campos de prompt **separados** (`subject`/`action`/`environment`/`composition`/`camera`/`lighting`/`mood`/`style`/`era`/`constraints`/`aspect_ratio` — nunca un string único), la lista de `references` (`{"asset_id", "role"}` — `role` uno de `character`/`style`/`location`/`object`/`archive`/`previous_generation`; usar `known_reference_assets` de los personajes involucrados cuando existan, para continuidad), y `characters` (los `character_id` de la escena, para que `lab/media/generation.py` pueda hacer el bootstrap de referencia la primera vez). Para `EDITED_IMAGE`, agregar `parent_asset_id` (el asset a editar) y `operation: "edit"`; para `GENERATED_IMAGE`, `operation: "generate"`. Escribir todo en `generation_requests.json`, con `status: "PENDING"` en cada uno. Esquema completo con ejemplos: `docs/LAB_MEDIA_ASSETS.md`.

8. Crear el blueprint conector:
   ```
   lab/.venv/Scripts/python.exe -m lab.cli media-record-plan <story_id>
   ```
   Este comando valida que `media_plan.json`/`generation_requests.json`/`visual_style.json` sean coherentes, crea `media_blueprint.json`, registra el job `MEDIA_PLAN`, e imprime el resumen de costo-control (cuántas escenas de cada tipo, cuántas requieren generación real).

9. Reportar al usuario ese resumen en texto claro **antes** de que se gaste nada en generación real -- esto es intencional (sección de control de costos): el usuario decide si sigue con `/lab-generate-media` o ajusta el plan primero.

## Cuándo se detiene esta skill sola

Si se invocó vía `/lab-media-plan`, termina acá -- no genera ninguna imagen. La generación real ocurre en un paso aparte (`/lab-generate-media`, que reusa `media_plan.json`/`generation_requests.json` si ya existen en vez de volver a correr esta skill).
