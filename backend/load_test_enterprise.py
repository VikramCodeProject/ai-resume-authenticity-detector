"""
Enterprise load testing profile for current API contract.
Run with: locust -f backend/load_test_enterprise.py --host http://127.0.0.1:8000
"""

from locust.contrib.fasthttp import FastHttpUser
from locust import task, between
import random


class EnterpriseResumeUser(FastHttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        self.email = f"load{random.randint(10000, 99999)}@example.com"
        self.password = "LoadTest123!"

        register_payload = {
            "email": self.email,
            "password": self.password,
            "full_name": "Load User",
            "gdpr_consent": True,
            "role": "candidate",
        }
        self.client.post("/api/auth/register", json=register_payload, name="auth_register")

        login_response = self.client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
            name="auth_login",
        )
        if login_response.status_code == 200:
            payload = login_response.json()
            self.access_token = payload.get("access_token")
        else:
            self.access_token = None

    def auth_headers(self):
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    @task(4)
    def upload_resume(self):
        if not self.access_token:
            return
        files = {
            "file": (
                "resume.pdf",
                b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF",
                "application/pdf",
            )
        }
        self.client.post(
            "/api/resumes/upload",
            files=files,
            headers=self.auth_headers(),
            name="resume_upload",
        )

    @task(3)
    def dashboard_stats(self):
        if not self.access_token:
            return
        self.client.get(
            "/api/dashboard/stats",
            headers=self.auth_headers(),
            name="dashboard_stats",
        )

    @task(2)
    def github_verification(self):
        self.client.post(
            "/api/verify/github",
            json={"username": "octocat", "claimed_skills": ["python", "fastapi"]},
            name="verify_github",
        )

    @task(1)
    def ai_health(self):
        self.client.get("/api/ai/health", name="ai_health")
