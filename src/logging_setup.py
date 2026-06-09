"""Structured logging for LTW (structlog + optional JSON file per run)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog


def configure_logging(
    *,
    level: str = "INFO",
    json_file: Path | None = None,
    run_id: str | None = None,
) -> None:
    """Configure stdlib + structlog for CLI/GUI runs."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if run_id:
        structlog.contextvars.bind_contextvars(run_id=run_id)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer() if json_file is None else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=log_level, format="%(message)s", stream=sys.stderr)

    if json_file is not None:
        json_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(json_file, encoding="utf-8")
        fh.setLevel(log_level)
        fh.setFormatter(logging.Formatter("%(message)s"))
        root = logging.getLogger()
        root.addHandler(fh)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
