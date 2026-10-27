import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJsonFormatter(logging.Formatter):
    """
    Structured JSON formatter for industrial surveillance & audit logging.
    Preserves audit trails for ingestion, validation, alerts, and provenance.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include structured context if attached to record
        if hasattr(record, "structured_data") and isinstance(record.structured_data, dict):
            # Sanitize secrets if any
            sanitized = {
                k: ("***" if "secret" in k.lower() or "key" in k.lower() or "password" in k.lower() else v)
                for k, v in record.structured_data.items()
            }
            log_payload["context"] = sanitized

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("smart_guardian")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
