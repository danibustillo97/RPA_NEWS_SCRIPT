"""
Proveedor: Cloudflare Workers AI. Habilitado hoy para generacion real
UNICAMENTE con @cf/black-forest-labs/flux-1-schnell (segundo MediaProvider,
ver docs/LAB_MEDIA_INTELLIGENCE.md seccion Providers) -- flux-2-dev quedo
descartado (timeouts reales del lado de Cloudflare, ver hallazgo en esa
misma doc); no se reintenta ni se agregan otros modelos.

Dos contratos REST distintos, verificados por separado contra la
documentacion oficial de Cloudflare (no inventados, y NO intercambiables
entre si -- el payload de un modelo multi-referencia como flux-2-dev no
sirve para un modelo simple como flux-1-schnell):

1) Sin imagenes de entrada (el caso de flux-1-schnell -- no soporta imagen
   de entrada/referencia en absoluto, ni parametro de tamano):

    POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{MODEL}
    Authorization: Bearer {API_TOKEN}
    Content-Type: application/json
    { "prompt": "...", "steps": 4 }

   Input schema documentado de flux-1-schnell: `prompt` (string, requerido,
   1-2048 chars), `steps` (int, opcional, default 4, maximo 8). Sin
   `width`/`height` -- el modelo no los acepta.

2) Con imagenes de entrada (modelos multi-referencia tipo flux-2-dev --
   camino conservado en el codigo por si se vuelve a habilitar ese modelo
   mas adelante, pero NO ejercitado/probado en esta fase):

    Content-Type: multipart/form-data
      prompt=...  width=... height=... steps=...
      input_image_0=@ref1.png  input_image_1=@ref2.png  ...  (hasta 4, binario)

Respuesta (sobre estandar de la API v4 de Cloudflare, igual para ambos):
    {"result": {"image": "<base64>"}, "success": true, "errors": [], "messages": []}
    {"result": null, "success": false, "errors": [{"code": ..., "message": ...}], "messages": []}
"""

import base64
import binascii
import json
import os
from typing import Optional

import requests

from lab.core.logging_setup import get_logger
from lab.media.providers.base import MediaProvider, MediaResult
from lab.media.providers._shared import sniff_mime_type

logger = get_logger(__name__)

_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
_MAX_INPUT_IMAGES = 4
# Default documentado por Cloudflare para flux-1-schnell (steps: default 4,
# máximo 8) -- "schnell" (alemán: "rápido") es el modelo optimizado para
# baja latencia, a diferencia de flux-2-dev.
_DEFAULT_STEPS = 4
_TIMEOUT_SECONDS = 300

# Tabla acotada de aspect_ratio -> (width, height), en multiplos de 8 (los
# valores que LAB usa hoy en sus generation_requests). No es una formula
# universal -- ver docs/LAB_MEDIA_INTELLIGENCE.md.
_ASPECT_RATIO_DIMENSIONS = {
    "1:1": (1024, 1024),
    "9:16": (576, 1024),
    "16:9": (1024, 576),
    "4:5": (896, 1120),
    "3:4": (896, 1184),
}
_DEFAULT_DIMENSIONS = (1024, 1024)


def _dimensions_for(aspect_ratio: str) -> tuple[int, int]:
    dims = _ASPECT_RATIO_DIMENSIONS.get(aspect_ratio)
    if dims is None:
        logger.warning(
            "CloudflareFluxProvider: aspect_ratio %r no está en la tabla conocida, "
            "usando default %s — agregar el valor real a _ASPECT_RATIO_DIMENSIONS si hace falta soportarlo",
            aspect_ratio, _DEFAULT_DIMENSIONS,
        )
        return _DEFAULT_DIMENSIONS
    return dims


class CloudflareFluxProvider(MediaProvider):
    name = "cloudflare"

    def __init__(self, model: str, account_id: Optional[str] = None, api_token: Optional[str] = None):
        import lab.config.settings  # noqa: F401 — dispara la carga de lab/config/.env

        self.account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN")
        if not self.account_id or not self.api_token:
            raise RuntimeError(
                "CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN no están configuradas "
                "(variables de entorno o lab/config/.env) — ver docs/LAB_SECURITY.md."
            )
        self.model = model
        self._url = f"{_API_BASE}/{self.account_id}/ai/run/{self.model}"

    def _call(self, prompt: str, aspect_ratio: str, images: list[bytes]) -> MediaResult:
        if len(images) > _MAX_INPUT_IMAGES:
            raise ValueError(
                f"CloudflareFluxProvider: {self.model} soporta hasta {_MAX_INPUT_IMAGES} "
                f"imágenes de entrada/referencia — se recibieron {len(images)}"
            )

        if images:
            return self._call_multipart(prompt, aspect_ratio, images)
        return self._call_json(prompt)

    def _call_json(self, prompt: str) -> MediaResult:
        """Formato verificado para flux-1-schnell: JSON plano, sin width/height
        (el modelo no los acepta) y sin imagen de entrada. Cualquier modelo sin
        imágenes de referencia usa este camino."""
        payload = {"prompt": prompt, "steps": _DEFAULT_STEPS}
        try:
            response = requests.post(
                self._url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                json=payload,
                timeout=_TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): timeout después de {_TIMEOUT_SECONDS}s") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): error de red — {exc}") from exc

        return self._parse_response(response, width=None, height=None)

    def _call_multipart(self, prompt: str, aspect_ratio: str, images: list[bytes]) -> MediaResult:
        """Formato para modelos multi-referencia (ej. flux-2-dev) -- conservado
        en el código pero no ejercitado en esta fase (ver docstring del módulo).
        No se setea Content-Type a mano: requests arma el boundary solo si se
        lo deja solo."""
        width, height = _dimensions_for(aspect_ratio)

        fields: dict[str, tuple] = {
            "prompt": (None, prompt),
            "width": (None, str(width)),
            "height": (None, str(height)),
            "steps": (None, str(_DEFAULT_STEPS)),
        }
        for i, img_bytes in enumerate(images):
            mime = sniff_mime_type(img_bytes)
            ext = mime.split("/")[-1] if "/" in mime else "png"
            fields[f"input_image_{i}"] = (f"reference_{i}.{ext}", img_bytes, mime)

        try:
            response = requests.post(
                self._url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                files=fields,
                timeout=_TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): timeout después de {_TIMEOUT_SECONDS}s") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): error de red — {exc}") from exc

        return self._parse_response(response, width=width, height=height)

    def _parse_response(self, response: "requests.Response", *, width: Optional[int], height: Optional[int]) -> MediaResult:
        status = response.status_code

        if status == 401:
            raise RuntimeError(
                f"Cloudflare Workers AI ({self.model}): 401 no autorizado — "
                "CLOUDFLARE_API_TOKEN inválido, expirado o sin permisos de Workers AI."
            )
        if status == 403:
            raise RuntimeError(
                f"Cloudflare Workers AI ({self.model}): 403 prohibido — "
                "verificar que el token tenga permiso sobre CLOUDFLARE_ACCOUNT_ID."
            )
        if status == 404:
            raise RuntimeError(
                f"Cloudflare Workers AI ({self.model}): 404 — modelo o cuenta no encontrados "
                "(revisar CLOUDFLARE_ACCOUNT_ID y el nombre del modelo)."
            )
        if status == 429:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): 429 — rate limit o cuota excedida.")
        if status >= 400:
            raise RuntimeError(
                f"Cloudflare Workers AI ({self.model}): HTTP {status} — {response.text[:500]}"
            )

        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): respuesta no es JSON válido") from exc

        if not isinstance(payload, dict) or not payload.get("success"):
            errors = payload.get("errors") if isinstance(payload, dict) else None
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): success=false, errors={errors}")

        result = payload.get("result") or {}
        b64_image = result.get("image") if isinstance(result, dict) else None
        if not b64_image:
            raise RuntimeError(
                f"Cloudflare Workers AI ({self.model}): la respuesta no trae result.image — "
                f"payload: {json.dumps(payload, ensure_ascii=False)[:500]}"
            )

        try:
            image_bytes = base64.b64decode(b64_image, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): no se pudo decodificar la imagen base64") from exc

        if not image_bytes:
            raise RuntimeError(f"Cloudflare Workers AI ({self.model}): imagen decodificada vacía")

        mime_type = sniff_mime_type(image_bytes)
        return MediaResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model=self.model,
            raw_meta={"requested_width": width, "requested_height": height},
        )

    def generate(self, prompt: str, *, aspect_ratio: str, references: Optional[list[bytes]] = None) -> MediaResult:
        return self._call(prompt, aspect_ratio, list(references or []))

    def edit(self, base_image: bytes, prompt: str, *, aspect_ratio: str, references: Optional[list[bytes]] = None) -> MediaResult:
        return self._call(prompt, aspect_ratio, [base_image, *(references or [])])

    def generate_from_references(self, prompt: str, references: list[bytes], *, aspect_ratio: str) -> MediaResult:
        if not references:
            raise ValueError("generate_from_references requiere al menos una referencia")
        return self._call(prompt, aspect_ratio, list(references))
