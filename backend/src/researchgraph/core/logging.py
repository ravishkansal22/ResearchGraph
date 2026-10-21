"""Structured Logging Configuration for ResearchGraph Backend."""

from __future__ import annotations

import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """Initialize structured console logging."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
