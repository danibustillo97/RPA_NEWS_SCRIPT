"""
Helpers compartidos entre providers concretos (gemini_image.py, cloudflare_flux.py).
No es un provider en si mismo -- prefijo _ a proposito.
"""

import io

_FORMAT_TO_MIME = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}


def sniff_mime_type(data: bytes) -> str:
    """Determina el mime type real abriendo la imagen con Pillow -- nunca se
    confia en una extension o en lo que reporte la API, se verifica el
    contenido real (ver docs/LAB_MEDIA_ASSETS.md)."""
    from PIL import Image

    with Image.open(io.BytesIO(data)) as img:
        return _FORMAT_TO_MIME.get(img.format or "", "application/octet-stream")
