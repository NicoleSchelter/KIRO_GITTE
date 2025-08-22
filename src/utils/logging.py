import logging
import os
from typing import Optional

class _DefaultFields(logging.Filter):
    """Sorgt dafür, dass optionale Felder existieren (verhindert KeyError im Formatter)."""
    _fields = ("request_id", "job_id", "status")

    def filter(self, record: logging.LogRecord) -> bool:
        for attr in self._fields:
            if not hasattr(record, attr):
                setattr(record, attr, "")
        return True

def _make_formatter() -> logging.Formatter:
    """JSON wenn LOG_FORMAT=json und python-json-logger vorhanden, sonst key=value."""
    timefmt = os.getenv("LOG_TIMEFMT", "%Y-%m-%dT%H:%M:%S%z")
    if os.getenv("LOG_FORMAT", "structured").lower() == "json":
        try:
            from pythonjsonlogger import jsonlogger  # optional
            return jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(job_id)s %(status)s",
                datefmt=timefmt,
            )
        except Exception:
            pass
    return logging.Formatter(
        fmt=("time=%(asctime)s level=%(levelname)s logger=%(name)s "
             "msg=%(message)s request_id=%(request_id)s job_id=%(job_id)s status=%(status)s"),
        datefmt=timefmt,
    )

_LOGGERS = {}

def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name in _LOGGERS:
        return _LOGGERS[name]
    logger = logging.getLogger(name or "gitte")
    if not logger.handlers:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, level, logging.INFO))
        handler = logging.StreamHandler()
        handler.addFilter(_DefaultFields())
        handler.setFormatter(_make_formatter())
        logger.addHandler(handler)
        logger.propagate = False
    _LOGGERS[name] = logger
    return logger
