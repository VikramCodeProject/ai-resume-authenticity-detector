from time import perf_counter

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response


resume_verification_requests_total = Counter(
    "resume_verification_requests_total",
    "Total resume verification API requests",
    ["endpoint", "method", "status_code"],
)

resume_verification_latency_seconds = Histogram(
    "resume_verification_latency_seconds",
    "Latency for resume verification API requests",
    ["endpoint", "method"],
)

ai_inference_time_seconds = Histogram(
    "ai_inference_time_seconds",
    "Time spent in AI inference",
    ["operation"],
)

blockchain_tx_time_seconds = Histogram(
    "blockchain_tx_time_seconds",
    "Blockchain transaction processing time",
    ["network"],
)

resume_verification_errors_total = Counter(
    "resume_verification_errors_total",
    "Total API errors",
    ["endpoint", "error_type"],
)


async def metrics_middleware(request: Request, call_next):
    started = perf_counter()
    endpoint = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        latency = perf_counter() - started
        resume_verification_requests_total.labels(endpoint=endpoint, method=method, status_code=response.status_code).inc()
        resume_verification_latency_seconds.labels(endpoint=endpoint, method=method).observe(latency)
        if response.status_code >= 400:
            resume_verification_errors_total.labels(endpoint=endpoint, error_type="http_error").inc()
        return response
    except Exception:
        latency = perf_counter() - started
        resume_verification_requests_total.labels(endpoint=endpoint, method=method, status_code=500).inc()
        resume_verification_latency_seconds.labels(endpoint=endpoint, method=method).observe(latency)
        resume_verification_errors_total.labels(endpoint=endpoint, error_type="unhandled_exception").inc()
        raise


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
