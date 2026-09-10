"""
Vocabulario de una sola fuente de verdad para Fase 4.2 etapa 1 (Animation
Planning). Ver lab.sequence.constants para el equivalente de Fase 4.1.
"""

# Estrategia de animacion por shot. AI_VIDEO existe en el vocabulario desde
# ya (para no tener que rediseñar el esquema cuando llegue), pero
# lab.animation.planner.decide_strategy() no la produce todavia -- no hay
# criterio (humano o de skill) para decidir cuando un movimiento la
# necesita, y esta etapa no lo incluye a proposito.
ANIMATION_STRATEGIES = frozenset({"DETERMINISTIC", "AI_VIDEO"})

# Backend de ejecucion (etapa futura -- nada de esto se ejecuta aca).
RENDER_BACKENDS = frozenset({"FFMPEG_LOCAL", "AI_VIDEO"})

# Unica combinacion valida por estrategia -- nunca AI_VIDEO->FFMPEG_LOCAL ni
# DETERMINISTIC->AI_VIDEO.
STRATEGY_BACKEND_MAP = {
    "DETERMINISTIC": "FFMPEG_LOCAL",
    "AI_VIDEO": "AI_VIDEO",
}

# Mismo vocabulario conceptual que SEQUENCE_STATUS (lab.sequence.constants)
# -- redefinido aca, no importado: mismo criterio ya usado entre
# lab.sequence y lab.media, cada paquete es autocontenido.
ANIMATION_PLAN_STATUS = frozenset({
    "DRAFT",
    "READY_FOR_REVIEW",
    "APPROVED",
    "REJECTED",
})
