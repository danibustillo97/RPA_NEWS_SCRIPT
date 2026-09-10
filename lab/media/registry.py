"""
asset_registry.json -- ledger append-only de assets realmente generados y
guardados (docs/LAB_MEDIA_ASSETS.md). Un fallo de generacion nunca crea un
registro aca -- ver lab/media/generation.py.

requested_aspect_ratio vs actual_aspect_ratio (ver docs/LAB_MEDIA_ASSETS.md):
un provider puede ignorar el aspect_ratio pedido (ej. flux-1-schnell siempre
produce 1024x1024 sin importar lo pedido) -- confundir ambos conceptos bajo
un solo campo "aspect_ratio" le hacia creer al registro que el archivo tenia
la forma pedida cuando no era asi. register_asset() SIEMPRE deriva
actual_aspect_ratio de width/height reales, nunca de lo que se pidio.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from lab.media.constants import ASSET_STATUS, PROVENANCE_VALUES
from lab.media.paths import asset_registry_path


def _derive_aspect_ratio(width: Optional[int], height: Optional[int]) -> Optional[str]:
    """Deriva el aspect ratio real a partir de dimensiones reales -- nunca del
    request. None si no hay width/height (nunca se inventa un valor)."""
    if not width or not height:
        return None
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def _load(story_id: str) -> list[dict[str, Any]]:
    path = asset_registry_path(story_id)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save(story_id: str, assets: list[dict[str, Any]]) -> None:
    path = asset_registry_path(story_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8")


def list_assets(story_id: str) -> list[dict[str, Any]]:
    return _load(story_id)


def get_asset(story_id: str, asset_id: str) -> Optional[dict[str, Any]]:
    for asset in _load(story_id):
        if asset["asset_id"] == asset_id:
            return asset
    return None


def register_asset(
    story_id: str,
    *,
    asset_id: str,
    scene_id: str,
    type_: str,
    subtype: str,
    filename: str,
    relative_path: str,
    mime_type: str,
    width: Optional[int],
    height: Optional[int],
    requested_aspect_ratio: Optional[str],
    source: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    prompt_version: Optional[int],
    parent_asset_id: Optional[str],
    references: list[dict[str, Any]],
    provenance: str,
    status: str = "READY",
) -> dict[str, Any]:
    if provenance not in PROVENANCE_VALUES:
        raise ValueError(f"provenance inválida: {provenance!r} (válidas: {sorted(PROVENANCE_VALUES)})")
    if status not in ASSET_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(ASSET_STATUS)})")

    record = {
        "asset_id": asset_id,
        "story_id": story_id,
        "scene_id": scene_id,
        "type": type_,
        "subtype": subtype,
        "filename": filename,
        "relative_path": relative_path,
        "mime_type": mime_type,
        "width": width,
        "height": height,
        "requested_aspect_ratio": requested_aspect_ratio,
        "actual_aspect_ratio": _derive_aspect_ratio(width, height),
        "source": source,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "parent_asset_id": parent_asset_id,
        "references": references,
        "provenance": provenance,
        "status": status,
    }
    assets = _load(story_id)
    assets.append(record)
    _save(story_id, assets)
    return record


def update_asset_status(story_id: str, asset_id: str, status: str) -> dict[str, Any]:
    if status not in ASSET_STATUS:
        raise ValueError(f"status inválido: {status!r} (válidos: {sorted(ASSET_STATUS)})")
    assets = _load(story_id)
    for asset in assets:
        if asset["asset_id"] == asset_id:
            asset["status"] = status
            _save(story_id, assets)
            return asset
    raise ValueError(f"Asset {asset_id!r} no encontrado en la historia {story_id!r}")


def next_asset_id(story_id: str, prefix: str = "img") -> str:
    existing = {a["asset_id"] for a in _load(story_id)}
    n = 1
    while f"{prefix}_{n:03d}" in existing:
        n += 1
    return f"{prefix}_{n:03d}"
