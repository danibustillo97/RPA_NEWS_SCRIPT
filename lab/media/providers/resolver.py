"""
Unico punto donde un nombre de provider ("gemini"/"cloudflare") se convierte
en una instancia concreta de MediaProvider. lab/media/generation.py (el
"Media Agent" en terminos de ejecucion) importa solo resolve_media_provider
-- nunca GeminiImageProvider ni CloudflareFluxProvider directo. Asi se
agregan providers nuevos sin tocar generation.py.
"""

import os
from typing import Optional

from lab.media.constants import MEDIA_PROVIDERS
from lab.media.providers.base import MediaProvider


def resolve_media_provider(name: Optional[str] = None) -> MediaProvider:
    """Resuelve un MediaProvider por nombre. Si no se pasa `name`, usa
    LAB_MEDIA_PROVIDER del entorno (leido en el momento, no cacheado -- asi
    es testeable con monkeypatch.setenv sin recargar modulos), default
    "gemini" (comportamiento previo a agregar Cloudflare, sin cambios)."""
    from lab.config import settings  # dispara la carga de lab/config/.env

    provider_name = (name or os.environ.get("LAB_MEDIA_PROVIDER", "gemini")).strip().lower()

    if provider_name not in MEDIA_PROVIDERS:
        raise ValueError(
            f"Provider de media desconocido: {provider_name!r} (válidos: {sorted(MEDIA_PROVIDERS)})"
        )

    if provider_name == "gemini":
        from lab.media.providers.gemini_image import GeminiImageProvider
        return GeminiImageProvider(model=settings.GEMINI_IMAGE_MODEL)

    from lab.media.providers.cloudflare_flux import CloudflareFluxProvider
    return CloudflareFluxProvider(model=settings.CLOUDFLARE_IMAGE_MODEL)
