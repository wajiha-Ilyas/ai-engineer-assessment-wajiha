"""JSON log formatter — no extra dependencies."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    _SKIP = frozenset(logging.LogRecord.__dict__)

    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Attach any extra fields passed via extra={...} or LoggerAdapter
        for key, val in record.__dict__.items():
            if key not in self._SKIP and not key.startswith("_"):
                obj[key] = val
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
