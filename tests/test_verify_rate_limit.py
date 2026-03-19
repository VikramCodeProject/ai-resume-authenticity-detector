from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from main import app  # noqa: E402
from utils.rate_limiter import limiter  # noqa: E402


def _post_n_times(client: TestClient, url: str, n: int, **kwargs):
    return [client.post(url, **kwargs).status_code for _ in range(n)]


def _assert_10_then_429(statuses):
    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429


def test_verify_github_rate_limit_11th_request_returns_429():
    limiter.request_history.clear()
    client = TestClient(app, base_url="http://127.0.0.1")

    # Rate limit check happens before Celery task submission,
    # so we don't need to patch the task itself
    statuses = _post_n_times(
        client,
        "/api/verify/github",
        11,
        json={"username": "testuser", "claimed_skills": ["python"]},
    )

    _assert_10_then_429(statuses)


def test_verify_full_rate_limit_11th_request_returns_429():
    limiter.request_history.clear()
    client = TestClient(app, base_url="http://127.0.0.1")

    statuses = _post_n_times(
        client,
        "/api/verify/full",
        11,
        json={
            "resume_id": "resume-123",
            "github_username": "testuser",
            "claimed_skills": ["python"],
            "certificate_image_paths": [],
        },
    )

    _assert_10_then_429(statuses)


def test_verify_resume_rate_limit_11th_request_returns_429():
    limiter.request_history.clear()
    client = TestClient(app, base_url="http://127.0.0.1")

    statuses = [
        client.post(
            "/api/verify/resume",
            files={"file": ("resume.txt", b"sample resume content", "text/plain")},
        ).status_code
        for _ in range(11)
    ]

    _assert_10_then_429(statuses)


def test_task_status_endpoint_is_not_rate_limited():
    limiter.request_history.clear()
    client = TestClient(app, base_url="http://127.0.0.1")

    with patch("api.routes.get_task_status", return_value={"task_id": "task-123", "status": "PENDING", "ready": False}):
        statuses = [
            client.get("/api/task-status/task-123").status_code
            for _ in range(11)
        ]

    assert statuses == [200] * 11
