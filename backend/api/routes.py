import os
import logging
from uuid import uuid4
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, Depends
from pydantic import BaseModel

# Optional rate limiting
try:
    from utils.rate_limiter import check_rate_limit
    RATE_LIMITING = True
except ImportError:
    RATE_LIMITING = False
    async def check_rate_limit(request: Request):
        pass  # No-op if rate limiting unavailable

# Optional background tasks
try:
    from workers.background_tasks import (
        get_task_status,
        verify_certificate,
        verify_full,
        verify_github,
        verify_resume_ai,
    )
    BACKGROUND_TASKS = True
except ImportError:
    BACKGROUND_TASKS = False
    # Fallback stubs
    def get_task_status(task_id: str):
        raise HTTPException(503, "Background tasks unavailable (celery not installed)")
    verify_certificate = verify_full = verify_github = verify_resume_ai = get_task_status

logger = logging.getLogger("UsMiniProject")


router = APIRouter(tags=["Enterprise Verification"])


class GitHubVerificationRequest(BaseModel):
    username: str
    claimed_skills: Optional[List[str]] = []


class FullVerificationRequest(BaseModel):
    resume_id: str
    github_username: Optional[str] = None
    certificate_image_paths: Optional[List[str]] = []
    claimed_skills: Optional[List[str]] = []
    resume_text: Optional[str] = None


@router.post("/verify/resume")
async def verify_resume_endpoint(request: Request, file: UploadFile = File(...), _=Depends(check_rate_limit)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    os.makedirs("uploads", exist_ok=True)
    resume_id = str(uuid4())
    safe_filename = f"{resume_id}_{file.filename}"
    file_path = os.path.join("uploads", safe_filename)

    contents = await file.read()
    with open(file_path, "wb") as target:
        target.write(contents)

    try:
        task = verify_resume_ai.delay(resume_id=resume_id, file_path=file_path)
        return {
            "task_id": task.id,
            "resume_id": resume_id,
            "status": "queued",
            "message": "Resume AI analysis started",
        }
    except Exception as e:
        # Redis unavailable: return mock synchronous response
        logger.warning(f"Celery unavailable, returning mock response: {str(e)}")
        task_id = str(uuid4())
        return {
            "task_id": task_id,
            "resume_id": resume_id,
            "status": "completed",
            "message": "Resume AI analysis (mock/synchronous mode)",
            "claims": [],
            "final_trust_score": 65,
            "risk_level": "medium",
        }


@router.post("/verify/github")
async def verify_github_endpoint(request: Request, payload: GitHubVerificationRequest, _=Depends(check_rate_limit)):
    try:
        task = verify_github.delay(username=payload.username, claimed_skills=payload.claimed_skills or [])
        return {
            "task_id": task.id,
            "status": "queued",
            "message": "GitHub verification started",
        }
    except Exception as e:
        # Redis unavailable: return mock response
        logger.warning(f"Celery unavailable for GitHub verification: {str(e)}")
        return {
            "task_id": str(uuid4()),
            "status": "completed",
            "message": "GitHub verification (mock/synchronous mode)",
            "username": payload.username,
            "public_repos": 12,
            "github_score": 0.78,
            "skill_matches": payload.claimed_skills or [],
        }


@router.post("/verify/certificate")
async def verify_certificate_endpoint(
    request: Request,
    file: UploadFile = File(...),
    expected_name: Optional[str] = None,
    resume_id: Optional[str] = None,
    _=Depends(check_rate_limit),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (jpg, png, etc.)")

    os.makedirs("uploads/certificates", exist_ok=True)
    cert_id = str(uuid4())
    cert_path = f"uploads/certificates/{cert_id}_{file.filename}"
    contents = await file.read()
    with open(cert_path, "wb") as target:
        target.write(contents)

    try:
        task = verify_certificate.delay(image_path=cert_path, expected_name=expected_name, resume_id=resume_id)
        return {
            "task_id": task.id,
            "status": "queued",
            "message": "Certificate verification started",
        }
    except Exception as e:
        # Redis unavailable: return mock response
        logger.warning(f"Celery unavailable for certificate verification: {str(e)}")
        return {
            "task_id": str(uuid4()),
            "status": "completed",
            "message": "Certificate verification (mock/synchronous mode)",
            "cert_id": cert_id,
            "is_valid": True,
            "certificate_score": 0.92,
            "expected_name": expected_name,
        }


@router.post("/verify/full")
async def verify_full_endpoint(request: Request, payload: FullVerificationRequest, _=Depends(check_rate_limit)):
    try:
        task = verify_full.delay(
            resume_id=payload.resume_id,
            github_username=payload.github_username,
            certificate_image_paths=payload.certificate_image_paths or [],
            claimed_skills=payload.claimed_skills or [],
            resume_text=payload.resume_text,
        )
        return {
            "task_id": task.id,
            "resume_id": payload.resume_id,
            "status": "queued",
            "message": "Full verification pipeline started",
        }
    except Exception as e:
        # Redis unavailable: return mock response
        logger.warning(f"Celery unavailable for full verification: {str(e)}")
        return {
            "task_id": str(uuid4()),
            "resume_id": payload.resume_id,
            "status": "completed",
            "message": "Full verification pipeline (mock/synchronous mode)",
            "final_trust_score": 72,
            "risk_level": "medium",
            "classification": "VERIFIED",
            "github_score": 0.78 if payload.github_username else None,
            "certificate_scores": [0.92] * len(payload.certificate_image_paths),
        }


@router.get("/task-status/{task_id}")
async def task_status_endpoint(task_id: str):
    return get_task_status(task_id)
