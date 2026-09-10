"""
Configuración local de LAB. Nada de secretos acá — solo límites y
comportamiento. La API key real (Gemini, Fase 3) se lee de variable de
entorno, nunca hardcodeada — ver lab/config/.env.example y docs/LAB_SECURITY.md.
"""

import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load_env_file() -> None:
    """Carga lab/config/.env (si existe) en os.environ, sin pisar variables
    que ya estén seteadas en el entorno real. Parser manual deliberado —
    formato KEY=VALUE trivial, no amerita agregar python-dotenv como
    dependencia nueva (ver docs/LAB_SECURITY.md)."""
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


_load_env_file()

# Tope de items por corrida de ingestión (mismo criterio que main.py: no
# hace sentido traer materia prima sin límite en una sola corrida).
MAX_INGESTION_ITEMS = int(os.environ.get("LAB_MAX_INGESTION_ITEMS", "30"))

# Útil para pruebas rápidas: limitar a las primeras N fuentes en vez de
# las 54 completas. None = todas.
MAX_SOURCES_OVERRIDE: int | None = (
    int(os.environ["LAB_MAX_SOURCES"]) if os.environ.get("LAB_MAX_SOURCES") else None
)

# Fase 3 — Media Intelligence: modelo de generación/edición de imágenes de
# Gemini. Único lugar donde se decide el nombre del modelo — nunca
# hardcodeado en lab/media/providers/gemini_image.py ni en ningún otro
# lado. El nombre puede cambiar con el tiempo (ver docs/LAB_MEDIA_INTELLIGENCE.md).
GEMINI_IMAGE_MODEL = os.environ.get("LAB_GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")

# Segundo provider de imagen — mismo criterio que arriba, nunca hardcodeado
# en lab/media/providers/cloudflare_flux.py. Default flux-1-schnell (no
# flux-2-dev): flux-2-dev quedó descartado por timeouts reales del lado de
# Cloudflare, ver docs/LAB_MEDIA_INTELLIGENCE.md.
CLOUDFLARE_IMAGE_MODEL = os.environ.get("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

# Provider por default cuando no se pide uno explícito (lab.cli media-generate
# --provider, o el params de un job). lab.media.providers.resolver lee
# LAB_MEDIA_PROVIDER de os.environ directo (no esta constante) para que sea
# testeable sin recargar el módulo — esta línea queda como referencia/default
# documentado, mismo valor.
MEDIA_PROVIDER = os.environ.get("LAB_MEDIA_PROVIDER", "gemini")
