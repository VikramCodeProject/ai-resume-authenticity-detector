from pathlib import Path
import sys
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from main import app  # noqa: E402


def _register_and_login(client: TestClient, email: str, password: str):
    register_payload = {
        "email": email,
        "password": password,
        "full_name": "Test User",
        "gdpr_consent": True,
        "role": "recruiter",
    }
    register_response = client.post("/api/auth/register", json=register_payload)
    assert register_response.status_code in (200, 201)

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()


def test_refresh_token_flow_returns_standard_success_contract():
    client = TestClient(app, base_url="http://127.0.0.1")
    tokens = _register_and_login(client, "refresh-contract@example.com", "Password123!")

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert "access_token" in body["data"]


def test_http_error_contract_shape_is_standardized():
    client = TestClient(app, base_url="http://127.0.0.1")

    response = client.get("/api/resumes/does-not-exist")

    assert response.status_code == 401
    body = response.json()
    assert body["error"] is True
    assert isinstance(body["message"], str)
    assert body["code"] == 401


def test_verify_github_direct_mode_uses_service_result():
    client = TestClient(app, base_url="http://127.0.0.1")

    async_result = {
        "username": "octocat",
        "github_authenticity_score": 88.0,
        "risk_level": "Low",
    }

    # Patch verify_github Celery task to raise error, triggering fallback to direct service
    import api.routes as routes_module
    original_verify_github = routes_module.verify_github
    
    mock_verify_github = MagicMock()
    mock_verify_github.delay = MagicMock(side_effect=RuntimeError("celery-down"))
    routes_module.verify_github = mock_verify_github

    with patch("api.routes.get_github_service") as mock_service_get:
        mock_service = mock_service_get.return_value
        mock_service.verify_profile = AsyncMock(return_value=async_result)

        response = client.post(
            "/api/verify/github",
            json={"username": "octocat", "claimed_skills": ["python"]},
        )
    
    # Restore original
    routes_module.verify_github = original_verify_github

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["username"] == "octocat"
    assert body["data"]["github_authenticity_score"] == 88.0
