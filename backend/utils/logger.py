import logging
import os
from logging.handlers import RotatingFileHandler
from time import perf_counter

from pythonjsonlogger import jsonlogger
from starlette.requests import Request


SERVICE_NAME = os.getenv("SERVICE_NAME", "resume-verifier")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")


def setup_logging() -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


async def request_logging_middleware(request: Request, call_next):
    logger = get_logger("api.request")
    started = perf_counter()

    try:
        response = await call_next(request)
        latency_ms = round((perf_counter() - started) * 1000, 2)
        logger.info(
            "Incoming API request",
            extra={
                "timestamp": request.scope.get("time", ""),
                "service": SERVICE_NAME,
                "endpoint": request.url.path,
                "method": request.method,
                "status": "success" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response
    except Exception:
        latency_ms = round((perf_counter() - started) * 1000, 2)
        logger.exception(
            "Unhandled request error",
            extra={
                "service": SERVICE_NAME,
                "endpoint": request.url.path,
                "method": request.method,
                "status": "error",
                "latency_ms": latency_ms,
            },
        )
        raise
