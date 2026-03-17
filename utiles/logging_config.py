import logging
import os
import sys


def setup_logging(level: str | None = None) -> None:
    """Configura logging para todo el proyecto. Llamar una vez al inicio."""
    log_level = level or os.environ.get("CARTOLAS_LOG_LEVEL", "INFO")

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )
