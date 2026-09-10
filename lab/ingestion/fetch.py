"""
Clasificación: ADAPT (docs/LAB_ARCHITECTURE_AUDIT.md sección N.2).
Extraído de `main.py :: fetch_news()` — misma lógica de recorrer fuentes
y armar candidatos (título, url, fecha), sin ninguno de los pasos que
seguían en `main.py` (dedup contra Supabase, guardado, categorización).
Ese es justo el punto: acá la ingestión entrega materia prima cruda, no
decide nada más.
"""

import logging
from dataclasses import dataclass
from datetime import timezone

import dateparser
import requests
from bs4 import BeautifulSoup

from lab.ingestion.sources import NEWS_SOURCES

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
LINK_HINT_PATTERNS = (
    "noticia", "news", "/202", "junior", "colombia", "politica",
    "deporte", "economia", "cultura", "salud",
)
MIN_LINK_TEXT_LENGTH = 40


@dataclass
class Candidate:
    title: str
    url: str
    source: str
    published_at: str | None  # ISO 8601, si se pudo determinar


def _clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def fetch_candidates(sources: list[str] | None = None) -> list[Candidate]:
    """Visita cada fuente y devuelve links candidatos a noticia.

    No descarga el cuerpo del artículo todavía (eso es `extract.py`) — acá
    solo se recorre la portada de cada fuente, igual que hacía
    `main.py::fetch_news`.
    """
    sources = sources if sources is not None else NEWS_SOURCES
    candidates: list[Candidate] = []

    for src in sources:
        logger.info("Revisando fuente: %s", src)
        try:
            res = requests.get(src, timeout=REQUEST_TIMEOUT)
            soup = BeautifulSoup(res.text, "html.parser")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error visitando fuente %s: %s", src, exc)
            continue

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = _clean_text(a.get_text())
            if len(text) <= MIN_LINK_TEXT_LENGTH or not any(p in href for p in LINK_HINT_PATTERNS):
                continue

            full_url = href if href.startswith("http") else src.rstrip("/") + "/" + href.lstrip("/")

            published_at = None
            try:
                time_tag = a.find_previous("time") or a.find_next("time")
                parsed = dateparser.parse(time_tag.get_text()) if time_tag else None
                if not parsed:
                    meta = soup.find("meta", attrs={"property": "article:published_time"})
                    parsed = dateparser.parse(meta["content"]) if meta and meta.get("content") else None
                if parsed and not parsed.tzinfo:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                published_at = parsed.isoformat() if parsed else None
            except Exception as exc:  # noqa: BLE001
                logger.debug("No se pudo parsear fecha en %s: %s", full_url, exc)

            candidates.append(Candidate(title=text, url=full_url, source=src, published_at=published_at))

    return candidates
