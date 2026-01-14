"""Structured logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from .config import LogLevel


def setup_logging(log_level: LogLevel = LogLevel.INFO) -> None:
    """Configure structured logging for the application."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.value),
    )

    # Define processors for structlog
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Use JSON renderer for production, console for development
    if log_level == LogLevel.DEBUG:
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure formatter for standard library handlers
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Apply formatter to root logger handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_context(**kwargs: Any) -> structlog.contextvars.bound_contextvars:
    """Context manager for adding context to all log messages within scope."""
    return structlog.contextvars.bound_contextvars(**kwargs)
