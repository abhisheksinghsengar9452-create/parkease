"""Structured application logging without secrets or credentials."""
from __future__ import annotations
import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    dictConfig({"version": 1, "disable_existing_loggers": False,
        "formatters": {"standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
        "root": {"handlers": ["console"], "level": level}})
