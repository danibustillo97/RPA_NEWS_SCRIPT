"""
Animation Planning de LAB (Fase 4.2, etapa 1).

Convierte sequence.json (Fase 4.1) en animation_plan.json: por cada shot,
que estrategia de animacion aplica (DETERMINISTIC vs AI_VIDEO) y una
instruccion de movimiento declarativa. Esta etapa es 100% Python
deterministico -- no hay skill todavia (la clasificacion DETERMINISTIC es
derivable directo del vocabulario MOTION_TYPES que Fase 4.1 ya usa), no hay
comando CLI, no hay Render Planner, no hay Renderer ni VideoProvider, y
sobre todo: NO se ejecuta ningun movimiento ni se genera ningun video.

Capa puramente aditiva: lee sequence.json/media_blueprint.json/
asset_registry.json, nunca los modifica. Ver docs/LAB_ANIMATION_ENGINE.md.
"""
