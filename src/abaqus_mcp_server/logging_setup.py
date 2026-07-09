"""Logging setup for the MCP server.

All logging goes to **stderr** because stdout carries JSON-RPC messages
in the stdio transport.
"""

from __future__ import annotations

import logging
import os


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger to write to stderr.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to the ``ABAQUS_MCP_LOG_LEVEL`` env var, or ``WARNING``.
    """
    if level is None:
        level = os.environ.get("ABAQUS_MCP_LOG_LEVEL", "WARNING")

    numeric_level = getattr(logging, level.upper(), logging.WARNING)

    handler = logging.StreamHandler()  # defaults to stderr
    handler.setFormatter(
        logging.Formatter(
            "[%(levelname)-8s] %(name)s: %(message)s",
        )
    )

    root = logging.getLogger()
    root.setLevel(numeric_level)
    # Remove any existing handlers to avoid duplicates
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
