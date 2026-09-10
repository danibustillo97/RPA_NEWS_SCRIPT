"""
Vocabulario de una sola fuente de verdad para Fase 3 (Media Intelligence).
Reusado por el Decision Engine (skill lab-media-planning), lab/media/*.py
y la validacion del CLI -- nunca redefinido en otro lado.
"""

# Tipos de media que el Decision Engine puede asignar a una escena. Solo
# GENERATED_IMAGE y EDITED_IMAGE tienen un provider real que los ejecuta
# en Fase 3 -- el resto es vocabulario preparado para fases futuras (ver
# docs/LAB_MEDIA_INTELLIGENCE.md, seccion "fuera de alcance").
MEDIA_TYPES = frozenset({
    "REAL_IMAGE",
    "GENERATED_IMAGE",
    "EDITED_IMAGE",
    "ARCHIVE_MEDIA",
    "VIDEO",
    "GENERATED_VIDEO",
    "AUDIO",
    "GRAPHIC",
    "TEXT_ONLY",
    "NO_MEDIA",
})

# Tipos que lab/media/generation.py sabe ejecutar de verdad hoy.
EXECUTABLE_MEDIA_TYPES = frozenset({"GENERATED_IMAGE", "EDITED_IMAGE"})

# Procedencia de un asset -- taxonomia NO INVENTAR aplicada a media (ver
# lab.editorial.artifacts para el equivalente de Fase 2 sobre texto).
PROVENANCE_VALUES = frozenset({
    "REAL_SOURCE",
    "ARCHIVE",
    "AI_GENERATED",
    "AI_EDITED",
    "USER_PROVIDED",
    "DERIVED",
    "UNKNOWN",
})

# Ciclo de vida de un asset individual -- independiente del WorkflowState
# del WorkspaceItem (que no cambia en Fase 3, ver docs/LAB_MEDIA_INTELLIGENCE.md).
ASSET_STATUS = frozenset({"READY", "REJECTED", "REGENERATE", "FAILED"})

# Estado de un generation_request.
REQUEST_STATUS = frozenset({"PENDING", "DONE", "FAILED"})

# Roles validos para una referencia dentro de un generation_request.
REFERENCE_ROLES = frozenset({
    "character", "style", "location", "object", "archive", "previous_generation",
})

OPERATIONS = frozenset({"generate", "edit"})

# Providers de generacion/edicion de imagen registrados en
# lab.media.providers.resolver -- Media Agent nunca importa un provider
# concreto, solo pide uno de estos nombres.
MEDIA_PROVIDERS = frozenset({"gemini", "cloudflare"})
