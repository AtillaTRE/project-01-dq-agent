# src/logging_config.py
# Centralized logging config. JSON in prod, human-readable in dev.

import logging
import sys

from pythonjsonlogger import jsonlogger


def setup_logging(
    level: str = "INFO",
    service_name: str = "dq-agent",
    json_format: bool = True,
) -> logging.Logger:
    """Sets up structured logging."""
    logger = logging.getLogger(service_name)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # avoids duplicate handlers

    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        # Structured JSON for prod (Cloud Logging parses it automatically)
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={
                "asctime":  "timestamp",
                "levelname": "severity",
            },
        )
    else:
        # Human-readable for dev local
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
