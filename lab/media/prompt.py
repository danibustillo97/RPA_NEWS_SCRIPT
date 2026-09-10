"""
Construccion deterministica del prompt final a partir de los campos
estructurados de un generation_request (docs/LAB_MEDIA_ASSETS.md seccion
Prompt Engineering). Los campos persisten por separado -- este modulo solo
los concatena en el momento de llamar al provider, para poder auditar o
regenerar sin reconstruir el prompt a mano.
"""

from typing import Any

_FIELD_ORDER = [
    ("subject", "Sujeto"),
    ("action", "Acción"),
    ("environment", "Entorno"),
    ("composition", "Composición"),
    ("camera", "Cámara"),
    ("lighting", "Iluminación"),
    ("mood", "Mood"),
    ("style", "Estilo"),
    ("era", "Época"),
    ("constraints", "Restricciones"),
]


def build_prompt(prompt_spec: dict[str, Any]) -> str:
    lines = []
    for field, label in _FIELD_ORDER:
        value = prompt_spec.get(field)
        if value:
            lines.append(f"{label}: {value}")
    if not lines:
        raise ValueError("prompt_spec vacío — no hay nada que construir")
    return "\n".join(lines)
