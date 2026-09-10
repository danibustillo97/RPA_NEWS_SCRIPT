"""
Clasificación: ADAPT (docs/LAB_ARCHITECTURE_AUDIT.md sección N.2).
Extraído de `main.py :: extract_body()` / `extract_image_url()` — misma
lógica de "traer materia prima" de la página del artículo. Sin la parte
de `main.py::generate_content()` que concatenaba título+cuerpo como si
fuera "el contenido final": acá el cuerpo crudo se entrega tal cual, la
redacción real la hace el workflow editorial de Claude Code en fases
posteriores.
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
MAX_BODY_LENGTH = 3500
MIN_PARAGRAPH_LENGTH = 40


def extract_body(url: str) -> str:
    try:
        res = requests.get(url, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(res.text, "html.parser")

        desc = soup.find("meta", attrs={"name": "description"})
        paragraphs = soup.find_all("p")
        paragraph_text = " ".join(
            p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > MIN_PARAGRAPH_LENGTH
        )

        if desc and desc.get("content"):
            text = f"{desc['content'].strip()} {paragraph_text}"
        else:
            text = paragraph_text if paragraph_text else soup.get_text(" ", strip=True)

        text = re.sub(r"\s+", " ", text)
        text = ". ".join(dict.fromkeys(text.split(". ")))  # sin frases duplicadas
        return text[:MAX_BODY_LENGTH]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error extrayendo cuerpo de %s: %s", url, exc)
        return ""


def extract_image_url(url: str) -> str | None:
    try:
        res = requests.get(url, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(res.text, "html.parser")
        for selector in ["meta[property='og:image']", "img"]:
            tag = soup.select_one(selector)
            if tag:
                src = tag.get("content") if selector.startswith("meta") else tag.get("src")
                if src and not src.startswith("data:"):
                    return src
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error extrayendo imagen de %s: %s", url, exc)
    return None
