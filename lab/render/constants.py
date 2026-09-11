"""
Vocabulario de una sola fuente de verdad para Fase 4.2 etapa 3 (Render
Planning). Ver lab.animation.constants para el equivalente de la etapa
anterior.
"""

RENDER_PLAN_STATUS = frozenset({"DRAFT", "READY_FOR_REVIEW", "APPROVED", "REJECTED"})

# DONE/FAILED reservados para cuando exista ejecucion real (etapa futura) --
# esta etapa solo produce PENDING, nunca ejecuta nada.
RENDER_SHOT_STATUS = frozenset({"PENDING", "DONE", "FAILED"})

# suggested_transform (de Fase 4.1) que son geometria de escalado pura,
# calculable sin criterio editorial: CROP/FIT/EXTEND. COMPOSE/UNKNOWN no lo
# son -- quedan con computable=false, nunca se fabrica un numero para ellos.
GEOMETRY_COMPUTABLE_TRANSFORMS = frozenset({"CROP", "FIT", "EXTEND"})

# aspect_ratio -> (width, height), resoluciones estandar 1080-based. Tabla
# acotada, mismo criterio que _ASPECT_RATIO_DIMENSIONS en
# lab/media/providers/cloudflare_flux.py -- no es una formula universal.
TARGET_DIMENSIONS = {
    "1:1": (1080, 1080),
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "4:5": (1080, 1350),
    "3:4": (1080, 1440),
}
DEFAULT_TARGET_DIMENSIONS = (1080, 1080)
