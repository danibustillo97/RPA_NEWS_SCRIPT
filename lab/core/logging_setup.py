"""
Logging de LAB — un archivo por día en lab/logs/, más consola. Nada de
`print()` suelto: cada módulo pide su logger con `get_logger(__name__)`.
"""

import logging
from datetime import datetime, timezone

from lab.core.paths import LOGS_DIR, ensure_runtime_dirs

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    ensure_runtime_dirs()
    log_file = LOGS_DIR / f"lab-{datetime.now(timezone.utc):%Y-%m-%d}.log"

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
