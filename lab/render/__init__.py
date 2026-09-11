"""
Render Planning de LAB (Fase 4.2, etapa 3).

Convierte animation_plan.json (etapa 2 de integracion, sobre el planner de
la etapa 1) en render_plan.json: por cada shot, la geometria concreta
(dimensiones objetivo, padding/crop en pixeles) que un futuro Renderer
necesitaria -- solo cuando es matematica de escalado pura, derivable de
datos reales (dimensiones del asset + resolucion objetivo). Nunca decide
QUE tipo de transformacion hace falta (eso ya lo decidio la skill de
Fase 4.1), nunca ejecuta FFmpeg ni ningun otro motor, nunca genera video.

Capa puramente aditiva: lee animation_plan.json/asset_registry.json, nunca
los modifica. Sin skill, sin comando CLI todavia (etapa futura). Ver
docs/LAB_RENDER_ENGINE.md.
"""
