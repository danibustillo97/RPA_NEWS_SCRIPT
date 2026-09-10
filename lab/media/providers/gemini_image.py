"""
Proveedor real: Gemini (SDK oficial google-genai). generate()/edit()/
generate_from_references() son wrappers finos sobre la misma llamada de
fondo (client.models.generate_content con response_modalities=["IMAGE"]) --
lo unico que cambia es que va en `contents` (solo texto, o texto + imagenes
de referencia/base).

Verificado contra la documentacion oficial de google-genai antes de escribir
esto (google.genai, types.GenerateContentConfig, types.ImageConfig,
types.Part.from_bytes) -- ver docs/LAB_MEDIA_INTELLIGENCE.md.
"""

import os
from typing import Optional

from lab.core.logging_setup import get_logger
from lab.media.providers.base import MediaProvider, MediaResult
from lab.media.providers._shared import sniff_mime_type as _sniff_mime_type

logger = get_logger(__name__)


class GeminiImageProvider(MediaProvider):
    name = "gemini"

    def __init__(self, model: str, api_key: Optional[str] = None):
        from google import genai

        import lab.config.settings  # noqa: F401 — dispara la carga de lab/config/.env

        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY no está configurada (variable de entorno o lab/config/.env) — "
                "ver docs/LAB_SECURITY.md."
            )
        self.model = model
        self._client = genai.Client(api_key=key)

    def _reference_parts(self, references: Optional[list[bytes]]):
        from google.genai import types

        parts = []
        for ref_bytes in references or []:
            parts.append(types.Part.from_bytes(data=ref_bytes, mime_type=_sniff_mime_type(ref_bytes)))
        return parts

    def _call(self, contents: list, aspect_ratio: str) -> MediaResult:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )

        for part in response.parts:
            if part.inline_data:
                return MediaResult(
                    image_bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type or "image/png",
                    model=self.model,
                    raw_meta={"aspect_ratio": aspect_ratio},
                )
        raise RuntimeError(f"Gemini ({self.model}) no devolvió ninguna imagen en la respuesta.")

    def generate(self, prompt: str, *, aspect_ratio: str, references: Optional[list[bytes]] = None) -> MediaResult:
        contents = [prompt, *self._reference_parts(references)]
        return self._call(contents, aspect_ratio)

    def edit(self, base_image: bytes, prompt: str, *, aspect_ratio: str, references: Optional[list[bytes]] = None) -> MediaResult:
        from google.genai import types

        base_part = types.Part.from_bytes(data=base_image, mime_type=_sniff_mime_type(base_image))
        contents = [prompt, base_part, *self._reference_parts(references)]
        return self._call(contents, aspect_ratio)

    def generate_from_references(self, prompt: str, references: list[bytes], *, aspect_ratio: str) -> MediaResult:
        if not references:
            raise ValueError("generate_from_references requiere al menos una referencia")
        contents = [prompt, *self._reference_parts(references)]
        return self._call(contents, aspect_ratio)
