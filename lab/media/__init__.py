"""
Media Intelligence de LAB (Fase 3).

El juicio (que necesita cada escena, con que estilo, con que referencias,
como redactar el prompt) lo hace el razonamiento de Claude Code en la
skill lab-media-planning. Este paquete es la mitad determinística: llamar
al proveedor real (Gemini), guardar el archivo, registrar metadata y
provenance, actualizar el media_blueprint. Nunca genera contenido
editorial ni decide el criterio visual por su cuenta.

Ver docs/LAB_MEDIA_INTELLIGENCE.md y docs/LAB_MEDIA_ASSETS.md.
"""
