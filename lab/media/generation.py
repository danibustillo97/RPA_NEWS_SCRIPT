"""
Ejecucion determinística de un generation_request: resolver referencias,
construir el prompt, llamar al provider real, guardar el archivo, calcular
metadata real (Pillow), registrar el asset, actualizar el media_blueprint,
y marcar el request DONE/FAILED. Un fallo nunca crea un asset (docs/LAB_MEDIA_ASSETS.md).

Se registra como job reusando lab/core/job.py tal cual (sin modificarlo) --
un job por request ejecutado, tipo media_generation/media_edit/media_retry
segun corresponda.
"""

import io
import json
from typing import Any, Optional

from lab.core.job import create_and_run, register_job_type
from lab.core.logging_setup import get_logger
from lab.media import blueprint, registry
from lab.media.constants import OPERATIONS
from lab.media.paths import generation_requests_path, story_media_dir
from lab.media.prompt import build_prompt
from lab.media.providers.resolver import resolve_media_provider
from lab.media.storage import LocalStorageProvider

logger = get_logger(__name__)


def _load_requests(story_id: str) -> dict[str, Any]:
    path = generation_requests_path(story_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No hay generation_requests.json para {story_id!r} — correr /lab-media-plan primero"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _save_requests(story_id: str, data: dict[str, Any]) -> None:
    generation_requests_path(story_id).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _find_request(data: dict[str, Any], request_id: str) -> dict[str, Any]:
    for req in data["requests"]:
        if req["request_id"] == request_id:
            return req
    raise ValueError(f"generation_request {request_id!r} no encontrado")


def _resolve_reference_bytes(story_id: str, storage: LocalStorageProvider, asset_id: str) -> bytes:
    asset = registry.get_asset(story_id, asset_id)
    if asset is None:
        raise ValueError(f"Referencia a asset inexistente: {asset_id!r}")
    return storage.read(asset["relative_path"])


def _resolve_character_profile_path(story_id: str, character_id: str):
    from lab.media.paths import character_profiles_dir

    return character_profiles_dir(story_id) / f"{character_id}.json"


def _bootstrap_character_reference(story_id: str, characters: list[str], asset_id: str) -> None:
    for character_id in characters or []:
        path = _resolve_character_profile_path(story_id, character_id)
        if not path.exists():
            continue
        profile = json.loads(path.read_text(encoding="utf-8"))
        if not profile.get("known_reference_assets"):
            profile["known_reference_assets"] = [asset_id]
            path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Personaje %s: %s registrado como primera referencia", character_id, asset_id)


def _execute_request(params: dict[str, Any]) -> dict[str, Any]:
    story_id = params["story_id"]
    request_id = params["request_id"]

    data = _load_requests(story_id)
    request = _find_request(data, request_id)

    if request["operation"] not in OPERATIONS:
        raise ValueError(f"operation inválida: {request['operation']!r}")

    storage = LocalStorageProvider(root=story_media_dir(story_id))
    prompt_spec = request["prompt_spec"]
    prompt_text = build_prompt(prompt_spec)
    aspect_ratio = prompt_spec.get("aspect_ratio", "9:16")

    reference_bytes = [
        _resolve_reference_bytes(story_id, storage, ref["asset_id"])
        for ref in request.get("references", [])
    ]

    # Media Agent (esta función) nunca importa un provider concreto -- solo
    # pide uno por nombre. Si params trae "provider" (override puntual, ej.
    # --provider cloudflare) se usa ese; si no, resolve_media_provider() cae
    # a LAB_MEDIA_PROVIDER del entorno (default "gemini", sin cambios de
    # comportamiento respecto a antes de agregar Cloudflare).
    provider = resolve_media_provider(params.get("provider"))

    if request["operation"] == "edit":
        if not request.get("parent_asset_id"):
            raise ValueError(f"request {request_id!r} es una edición pero no trae parent_asset_id")
        base_bytes = _resolve_reference_bytes(story_id, storage, request["parent_asset_id"])
        result = provider.edit(base_bytes, prompt_text, aspect_ratio=aspect_ratio, references=reference_bytes or None)
        subtype = "edited"
        provenance = "AI_EDITED"
    else:
        if reference_bytes:
            result = provider.generate_from_references(prompt_text, reference_bytes, aspect_ratio=aspect_ratio)
        else:
            result = provider.generate(prompt_text, aspect_ratio=aspect_ratio)
        subtype = "generated"
        provenance = "AI_GENERATED"

    from PIL import Image

    with Image.open(io.BytesIO(result.image_bytes)) as img:
        width, height = img.size
        ext = (img.format or "PNG").lower()

    asset_id = registry.next_asset_id(story_id)
    filename = f"{request['scene_id']}-{asset_id}.{ext}"
    relative_path = f"images/{subtype}/{filename}"
    storage.save(relative_path, result.image_bytes)

    asset = registry.register_asset(
        story_id,
        asset_id=asset_id,
        scene_id=request["scene_id"],
        type_="image",
        subtype=subtype,
        filename=filename,
        relative_path=relative_path,
        mime_type=result.mime_type,
        width=width,
        height=height,
        requested_aspect_ratio=aspect_ratio,
        source=None,
        provider=provider.name,
        model=result.model,
        prompt_version=request.get("prompt_version", 1),
        parent_asset_id=request.get("parent_asset_id"),
        references=request.get("references", []),
        provenance=provenance,
        status="READY",
    )

    blueprint.add_asset_to_scene(story_id, request["scene_id"], asset_id)

    if request["operation"] == "generate":
        _bootstrap_character_reference(story_id, request.get("characters", []), asset_id)

    request["status"] = "DONE"
    request["result_asset_id"] = asset_id
    request["error"] = None
    _save_requests(story_id, data)

    return {"asset_id": asset_id, "scene_id": request["scene_id"], "relative_path": relative_path}


def _job_handler(params: dict[str, Any]) -> dict[str, Any]:
    story_id = params["story_id"]
    request_id = params["request_id"]
    try:
        return _execute_request(params)
    except Exception as exc:  # noqa: BLE001 — se registra en el request, no se oculta
        data = _load_requests(story_id)
        try:
            request = _find_request(data, request_id)
            request["status"] = "FAILED"
            request["error"] = str(exc)
            _save_requests(story_id, data)
        except ValueError:
            pass
        raise


register_job_type("media_generation")(_job_handler)
register_job_type("media_edit")(_job_handler)
register_job_type("media_retry")(_job_handler)


def _job_type_for(request: dict[str, Any]) -> str:
    if request.get("attempt", 1) > 1:
        return "media_retry"
    return "media_edit" if request["operation"] == "edit" else "media_generation"


def process_requests(
    story_id: str, request_id: Optional[str] = None, provider_name: Optional[str] = None
) -> list[dict[str, Any]]:
    """Procesa los requests PENDING de la historia (o uno solo si se pasa
    request_id). Cada request se ejecuta como su propio job (create_and_run),
    exactamente igual que run_scraper en Fase 1 — un fallo en un request no
    aborta los demás. `provider_name` es un override puntual (ej. --provider
    cloudflare); si no se pasa, cada request usa el provider configurado por
    default (LAB_MEDIA_PROVIDER) — sin fallback automático entre providers si
    el elegido falla (ver docs/LAB_MEDIA_INTELLIGENCE.md)."""
    data = _load_requests(story_id)
    targets = [r for r in data["requests"] if r["request_id"] == request_id] if request_id else [
        r for r in data["requests"] if r["status"] == "PENDING"
    ]
    if request_id and not targets:
        raise ValueError(f"generation_request {request_id!r} no encontrado")

    results = []
    for request in targets:
        job_type = _job_type_for(request)
        job = create_and_run(
            job_type,
            {"story_id": story_id, "request_id": request["request_id"], "provider": provider_name},
        )
        results.append({
            "request_id": request["request_id"],
            "scene_id": request["scene_id"],
            "job_id": job.id,
            "status": job.status.value,
            "result": job.result,
            "error": job.error,
        })
    return results


def retry_failed(story_id: str, request_id: str, provider_name: Optional[str] = None) -> dict[str, Any]:
    """Reintenta un request FAILED: lo vuelve a PENDING y lo corre de nuevo.
    No duplica el request ni crea un asset si vuelve a fallar (sección 19).
    `provider_name` permite reintentar con un provider distinto al que falló
    la vez anterior (override puntual, igual que en process_requests)."""
    data = _load_requests(story_id)
    request = _find_request(data, request_id)
    if request["status"] != "FAILED":
        raise ValueError(f"El request {request_id!r} no está FAILED (está {request['status']!r})")
    request["status"] = "PENDING"
    request["attempt"] = request.get("attempt", 1) + 1
    _save_requests(story_id, data)
    results = process_requests(story_id, request_id=request_id, provider_name=provider_name)
    return results[0]
