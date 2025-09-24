"""Logging helpers for rtsp2jpg."""

from __future__ import annotations

import logging
from logging import Logger

from .config import get_settings


def configure_logging() -> Logger:
    """Configure root logging once based on settings."""

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("rtsp2jpg")
    logger.setLevel(level)
    return logger
