import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
_configured = False


def set_request_id(value: str | None) -> None:
    request_id_var.set(value)


def get_request_id() -> str | None:
    return request_id_var.get()


def set_user_id(value: str | None) -> None:
    user_id_var.set(value)


def get_user_id() -> str | None:
    return user_id_var.get()


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
        }
        reserved = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "request_id",
            "user_id",
        }
        for key, value in record.__dict__.items():
            if key in reserved or key in payload:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "console").lower()
    log_file = os.getenv("LOG_FILE")
    # 默认日志文件路径
    if not log_file:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
    rotation_bytes = int(os.getenv("LOG_ROTATION_BYTES", str(10 * 1024 * 1024)))
    rotation_backups = int(os.getenv("LOG_ROTATION_BACKUPS", "5"))

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "json" if log_format == "json" else "console",
            "filters": ["context"],
        }
    }

    root_handlers = ["console"]

    if log_file:
        handlers["file"] = {
            "()": RotatingFileHandler,
            "filename": log_file,
            "maxBytes": rotation_bytes,
            "backupCount": rotation_backups,
            "encoding": "utf-8",
            "level": log_level,
            "formatter": "json" if log_format == "json" else "console",
            "filters": ["context"],
        }
        root_handlers.append("file")

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"context": {"()": ContextFilter}},
        "formatters": {
            "console": {
                "format": "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s user_id=%(user_id)s %(message)s"
            },
            "json": {"()": JsonFormatter},
        },
        "handlers": handlers,
        "root": {"level": log_level, "handlers": root_handlers},
        "loggers": {
            "uvicorn.error": {"level": log_level, "handlers": root_handlers, "propagate": False},
            "uvicorn.access": {"level": log_level, "handlers": root_handlers, "propagate": False},
            "urllib3": {"level": "WARNING"},
            "pymongo": {"level": "WARNING"},
            "motor": {"level": "WARNING"},
        },
    }

    dictConfig(config)
    _configured = True


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("app.request")

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        incoming_request_id = request.headers.get("X-Request-ID")
        request_id = incoming_request_id or uuid.uuid4().hex
        set_request_id(request_id)
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": getattr(response, "status_code", None),
                    "duration_ms": duration_ms,
                },
            )
            set_user_id(None)
            set_request_id(None)

        assert response is not None
        response.headers["X-Request-ID"] = request_id
        return response
