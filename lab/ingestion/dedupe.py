"""
Clasificación: REBUILD, adaptando el *patrón* de `visited_urls.txt`
(docs/LAB_ARCHITECTURE_AUDIT.md sección N.2/N.3).

`main.py` deduplica con dos mecanismos: una query en vivo a Supabase
(`is_duplicate`) y un archivo plano (`visited_urls.txt`). LAB no puede
usar el primero (cero dependencia de Supabase) y no comparte el segundo
(es el historial de producción, no el de LAB). Así que LAB tiene su
propio índice local, mismo espíritu que `visited_urls.txt` (un archivo,
sin red) pero en JSON y scoped a `lab/workspace/`.
"""

import json
from pathlib import Path

from lab.core.paths import DEDUPE_INDEX_FILE, ensure_runtime_dirs


def _load() -> dict[str, list[str]]:
    if not DEDUPE_INDEX_FILE.exists():
        return {"urls": [], "slugs": []}
    return json.loads(DEDUPE_INDEX_FILE.read_text(encoding="utf-8"))


def _save(index: dict[str, list[str]]) -> None:
    ensure_runtime_dirs()
    DEDUPE_INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def is_known(url: str, slug: str) -> bool:
    index = _load()
    return url in index["urls"] or slug in index["slugs"]


def mark_known(url: str, slug: str) -> None:
    index = _load()
    if url not in index["urls"]:
        index["urls"].append(url)
    if slug not in index["slugs"]:
        index["slugs"].append(slug)
    _save(index)


def count_known() -> int:
    return len(_load()["urls"])
