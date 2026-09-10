"""
Orquesta la ingestión completa: fetch -> extract -> quality gate -> dedupe
-> guardar en workspace/incoming (estado INGESTED).

Esto es lo que corre el job `run_scraper`. Responsabilidad única:
    FUENTES -> SCRAPER -> RAW/INGESTED CONTENT -> LAB WORKSPACE
No publica, no escribe Supabase, no corre nada editorial, no decide qué
historia "vale la pena" — eso es explícitamente de fases posteriores
(docs/LAB_ARCHITECTURE_AUDIT.md, brief de corrección de arquitectura).
"""

from typing import Any

from lab.core.job import register_job_type
from lab.core.logging_setup import get_logger
from lab.core.workspace import WorkflowState, WorkspaceItem, new_item_id, save_item
from lab.ingestion import dedupe
from lab.ingestion.extract import extract_body, extract_image_url
from lab.ingestion.fetch import fetch_candidates
from lab.ingestion.quality import is_valid_article, is_valid_image_url
from lab.ingestion.slug import generate_slug

logger = get_logger(__name__)

DEFAULT_MAX_ITEMS = 30


def run_ingestion(max_sources: int | None = None, max_items: int = DEFAULT_MAX_ITEMS) -> dict[str, Any]:
    from lab.ingestion.sources import NEWS_SOURCES

    sources = NEWS_SOURCES[:max_sources] if max_sources else NEWS_SOURCES
    logger.info("Ingestión: %d fuentes, tope %d items", len(sources), max_items)

    candidates = fetch_candidates(sources)
    logger.info("Candidatos encontrados: %d", len(candidates))

    saved = 0
    skipped_duplicate = 0
    skipped_quality = 0
    errors = 0

    for candidate in candidates:
        if saved >= max_items:
            break

        slug = generate_slug(candidate.title)
        if dedupe.is_known(candidate.url, slug):
            skipped_duplicate += 1
            continue

        try:
            content = extract_body(candidate.url)
            image_url = extract_image_url(candidate.url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error extrayendo %s: %s", candidate.url, exc)
            errors += 1
            continue

        if not is_valid_article(candidate.title, content) or not is_valid_image_url(image_url):
            skipped_quality += 1
            continue

        item = WorkspaceItem(
            id=new_item_id(),
            state=WorkflowState.INGESTED,
            title=candidate.title,
            source_url=candidate.url,
            source=candidate.source,
            image_url=image_url,
            content=content,
            published_at=candidate.published_at,
            extra={"slug": slug},
        )
        save_item(item)
        dedupe.mark_known(candidate.url, slug)
        saved += 1
        logger.info("Ingerido: %s | %s", item.id, item.title[:70])

    summary = {
        "sources_visited": len(sources),
        "candidates_found": len(candidates),
        "saved": saved,
        "skipped_duplicate": skipped_duplicate,
        "skipped_quality": skipped_quality,
        "errors": errors,
    }
    logger.info("Ingestión terminada: %s", summary)
    return summary


@register_job_type("run_scraper")
def run_scraper_job(params: dict[str, Any]) -> dict[str, Any]:
    return run_ingestion(
        max_sources=params.get("max_sources"),
        max_items=params.get("max_items", DEFAULT_MAX_ITEMS),
    )
