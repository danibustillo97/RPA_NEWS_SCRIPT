"""
Clasificación: ADAPT (docs/LAB_ARCHITECTURE_AUDIT.md sección N.2).
Idéntica a `generate_slug()` de `main.py` — utilidad pura, sin cambios
de lógica, solo movida a su propio módulo.
"""

import re
import unicodedata


def generate_slug(title: str) -> str:
    slug = unicodedata.normalize("NFKD", title.lower()).encode("ascii", "ignore").decode("utf-8")
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug
