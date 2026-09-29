import logging
import contextvars

from app.core.config import settings

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="n/a")


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str:
    return _request_id_var.get()


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("portal_transparencia")
    logger.setLevel(level.upper())
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


logger = configure_logging(settings.LOG_LEVEL)
logger.addFilter(RequestIdFilter())
