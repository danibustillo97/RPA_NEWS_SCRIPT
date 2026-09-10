"""
Abstraccion de proveedor de generacion/edicion de media (docs/LAB_MEDIA_INTELLIGENCE.md).
El resto de LAB habla contra esta interfaz -- generate()/edit()/
generate_from_references() -- nunca directo contra el SDK de un proveedor
especifico. Hoy solo existe GeminiImageProvider; el nombre del modelo es
configurable (lab/config/settings.py), nunca hardcodeado aca.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MediaResult:
    image_bytes: bytes
    mime_type: str
    model: str
    raw_meta: dict[str, Any]
    width: Optional[int] = None
    height: Optional[int] = None


class MediaProvider(ABC):
    # Nombre corto usado para registrar `provider` en asset_registry.json y
    # para la seleccion en lab.media.providers.resolver -- cada subclase lo
    # sobreescribe ("gemini", "cloudflare", ...). No abstracto a proposito:
    # agregar esto no rompe ninguna subclase existente.
    name: str = "unknown"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str,
        references: Optional[list[bytes]] = None,
    ) -> MediaResult:
        """Genera una imagen nueva a partir de un prompt de texto, opcionalmente
        guiada por imagenes de referencia (estilo, personaje, locacion...)."""

    @abstractmethod
    def edit(
        self,
        base_image: bytes,
        prompt: str,
        *,
        aspect_ratio: str,
        references: Optional[list[bytes]] = None,
    ) -> MediaResult:
        """Edita una imagen existente segun una instruccion en lenguaje natural.
        Siempre produce un asset nuevo -- nunca sobreescribe base_image."""

    @abstractmethod
    def generate_from_references(
        self,
        prompt: str,
        references: list[bytes],
        *,
        aspect_ratio: str,
    ) -> MediaResult:
        """Genera una imagen nueva usando varias referencias (tipicamente
        continuidad de personaje/estilo) como guia principal, no como edicion
        de una imagen base unica."""
