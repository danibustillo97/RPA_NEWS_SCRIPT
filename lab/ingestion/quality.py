"""
Clasificación: REUSE (docs/LAB_ARCHITECTURE_AUDIT.md sección N.2).
`is_valid_article` viene de `src/utils/validator.py`, la idea de
`is_valid_image_url` de `src/utils/media.py` (ajustada: `main.py` en
producción solo exige "no vacío / no placeholder", no una extensión de
archivo estricta, porque muchas imágenes reales vienen de URLs de CDN
sin extensión visible — se sigue el criterio que ya probó funcionar en
producción, no el más estricto que nunca se usó).

Estos son *gates de calidad de la materia prima* (¿hay título? ¿hay
imagen real?) — no son juicio editorial. La ingestión descarta lo que no
pasa acá; lo que sí pasa, pasa crudo, sin opinar sobre si es una buena
historia o no (eso es trabajo de Claude Code en fases posteriores).
"""

MIN_CONTENT_LENGTH = 200


def is_valid_article(title: str, content: str) -> bool:
    title = (title or "").strip()
    content = (content or "").strip()
    return bool(title) and len(content) >= MIN_CONTENT_LENGTH


def looks_like_placeholder(url: str | None) -> bool:
    if not url:
        return True
    return "placeholder.com" in url.lower()


def is_valid_image_url(url: str | None) -> bool:
    return bool(url) and not looks_like_placeholder(url)
