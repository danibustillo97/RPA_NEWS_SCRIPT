"""
Sequence & Animation Engine de LAB (Fase 4, primera etapa).

Convierte assets ya generados (Fase 3) + narrativa ya escrita (Fase 2) en
una representacion declarativa de una secuencia audiovisual -- orden,
duracion, encuadre, movimiento, transiciones -- SIN generar ni animar nada
todavia. El criterio narrativo (que shot va primero, que movimiento tiene
sentido) lo decide el razonamiento de Claude Code en la skill
lab-sequence-planning; este paquete es la mitad deterministica: validar
que las referencias (scene_id, asset_id) sean reales, derivar
transform_required de dimensiones reales, y guardar/leer sequence.json.

Ver docs/LAB_SEQUENCE_ENGINE.md.
"""
