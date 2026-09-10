"""
Vocabulario de una sola fuente de verdad para Fase 4 (Sequence Engine).
Ver lab.media.constants para el equivalente de Fase 3.
"""

# Movimiento declarativo por shot -- no se ejecuta en esta etapa, solo se
# describe (ver docs/LAB_SEQUENCE_ENGINE.md).
MOTION_TYPES = frozenset({
    "STATIC",
    "SLOW_ZOOM_IN",
    "SLOW_ZOOM_OUT",
    "PAN_LEFT",
    "PAN_RIGHT",
    "PAN_UP",
    "PAN_DOWN",
    "PUSH_IN",
    "PULL_OUT",
})

# Vocabulario propio de LAB -- el brief solo menciona FADE y CUT como
# ejemplos; este set es una decision de diseño razonable, extensible sin
# romper el esquema de sequence.json.
TRANSITION_TYPES = frozenset({
    "NONE",
    "CUT",
    "FADE",
    "DISSOLVE",
})

# Que hacer cuando actual_aspect_ratio de un asset no coincide con el
# target_aspect_ratio de la secuencia -- decision de la skill (criterio
# editorial), nunca de Python. UNKNOWN es valido cuando la skill no tiene
# suficiente informacion para decidir con confianza.
TRANSFORM_REQUIRED_VALUES = frozenset({
    "CROP",
    "FIT",
    "EXTEND",
    "COMPOSE",
    "UNKNOWN",
})

# Ciclo de vida de una secuencia -- vocabulario compatible con el de
# WorkflowState (lab/core/workspace.py), pero NO es ese enum: una secuencia
# no es un WorkspaceItem. No existe hoy ningun mecanismo de CLI para pasar
# de READY_FOR_REVIEW a APPROVED/REJECTED (tampoco existe para items ni
# assets) -- ver docs/LAB_SEQUENCE_ENGINE.md seccion Human Review.
SEQUENCE_STATUS = frozenset({
    "DRAFT",
    "READY_FOR_REVIEW",
    "APPROVED",
    "REJECTED",
})

# target_format es texto libre a proposito (ej. "REEL", "STORY") -- el brief
# no pide un vocabulario cerrado para esto, y content_plan.json de Fase 2 ya
# tiene su propia nocion de formato (NEWS/EXPLAINER/REEL/STORY/CAROUSEL/NONE)
# para la recomendacion editorial, que no es exactamente lo mismo que el
# formato de ENTREGA de una secuencia con movimiento -- inventar un tercer
# enum superpuesto no aporta, ver docs/LAB_SEQUENCE_ENGINE.md.
