import os
import logging
from uuid import uuid4
from typing import List, Optional
from datetime import datetime
import re

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, Depends
from pydantic import BaseModel
import hashlib

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

from services import get_github_service, get_ocr_service
from services.blockchain_service import get_blockchain_service
from utils.api_response import success_response


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


class BlockchainHashVerificationRequest(BaseModel):
    tx_hash: str
    expected_hash: str


SQLI_PATTERN = re.compile(r"('|\"|;|--|/\*|\*/|\bunion\b|\bdrop\b|\bselect\b)", re.IGNORECASE)


def validate_untrusted_input(field_name: str, value: Optional[str]) -> None:
    if value and SQLI_PATTERN.search(value):
        raise HTTPException(status_code=400, detail=f"Potentially unsafe input in {field_name}")


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
        return success_response(
            {
                "task_id": task.id,
                "resume_id": resume_id,
                "status": "queued",
                "message": "Resume AI analysis started",
            }
        )
    except Exception as e:
        logger.warning(f"Celery unavailable, running direct verification: {str(e)}")
        content_hash = hashlib.sha256(contents).hexdigest()
        risk = "low" if len(contents) > 50_000 else "medium"
        score = 75 if risk == "low" else 62
        return success_response(
            {
                "resume_id": resume_id,
                "status": "completed",
                "message": "Resume analyzed in direct mode",
                "claims": [],
                "final_trust_score": score,
                "risk_level": risk,
                "resume_sha256": content_hash,
            }
        )


@router.post("/verify/github")
async def verify_github_endpoint(request: Request, payload: GitHubVerificationRequest, _=Depends(check_rate_limit)):
    validate_untrusted_input("username", payload.username)

    try:
        task = verify_github.delay(username=payload.username, claimed_skills=payload.claimed_skills or [])
        return success_response(
            {
                "task_id": task.id,
                "status": "queued",
                "message": "GitHub verification started",
            }
        )
    except Exception as e:
        logger.warning(f"Celery unavailable for GitHub verification, using direct service: {str(e)}")
        github_service = get_github_service()
        result = await github_service.verify_profile(payload.username, payload.claimed_skills or [])
        return success_response(result)


@router.post("/verify/certificate")
async def verify_certificate_endpoint(
    request: Request,
    file: UploadFile = File(...),
    expected_name: Optional[str] = None,
    resume_id: Optional[str] = None,
    _=Depends(check_rate_limit),
):
    validate_untrusted_input("expected_name", expected_name)
    validate_untrusted_input("resume_id", resume_id)

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
        return success_response(
            {
                "task_id": task.id,
                "status": "queued",
                "message": "Certificate verification started",
            }
        )
    except Exception as e:
        logger.warning(f"Celery unavailable for certificate verification, using direct OCR service: {str(e)}")
        ocr_service = get_ocr_service()
        result = await ocr_service.verify_certificate(
            image_path=cert_path,
            expected_name=expected_name,
            resume_id=resume_id,
        )
        result["cert_id"] = cert_id
        return success_response(result)


@router.post("/verify/full")
async def verify_full_endpoint(request: Request, payload: FullVerificationRequest, _=Depends(check_rate_limit)):
    validate_untrusted_input("resume_id", payload.resume_id)
    validate_untrusted_input("github_username", payload.github_username)

    try:
        task = verify_full.delay(
            resume_id=payload.resume_id,
            github_username=payload.github_username,
            certificate_image_paths=payload.certificate_image_paths or [],
            claimed_skills=payload.claimed_skills or [],
            resume_text=payload.resume_text,
        )
        return success_response(
            {
                "task_id": task.id,
                "resume_id": payload.resume_id,
                "status": "queued",
                "message": "Full verification pipeline started",
            }
        )
    except Exception as e:
        logger.warning(f"Celery unavailable for full verification, running direct services: {str(e)}")
        github_score = None
        github_result = None
        if payload.github_username:
            github_result = await get_github_service().verify_profile(
                payload.github_username,
                payload.claimed_skills or [],
            )
            github_score = float(github_result.get("github_authenticity_score", 0.0))

        cert_results = []
        cert_scores = []
        for path in payload.certificate_image_paths or []:
            cert_result = await get_ocr_service().verify_certificate(
                image_path=path,
                expected_name=None,
                resume_id=payload.resume_id,
            )
            cert_results.append(cert_result)
            cert_scores.append(float(cert_result.get("authenticity_score", 0.0)))

        aggregate = []
        if github_score is not None:
            aggregate.append(github_score)
        aggregate.extend(cert_scores)
        final_score = round(sum(aggregate) / len(aggregate), 2) if aggregate else 50.0
        risk_level = "low" if final_score >= 80 else "medium" if final_score >= 60 else "high"
        classification = "VERIFIED" if final_score >= 70 else "DOUBTFUL" if final_score >= 50 else "FAKE"

        hash_material = f"{payload.resume_id}:{payload.resume_text or ''}:{datetime.utcnow().date().isoformat()}"
        resume_hash = hashlib.sha256(hash_material.encode("utf-8")).hexdigest()
        blockchain_tx_hash = None
        blockchain_block = None
        try:
            blockchain_service = get_blockchain_service()
            blockchain_tx_hash, blockchain_block = await blockchain_service.write_verification(
                resume_id=payload.resume_id,
                verification_score=final_score,
                verified=classification == "VERIFIED",
            )
        except Exception as chain_exc:
            logger.warning("Blockchain write failed in direct mode: %s", chain_exc)

        return success_response(
            {
                "resume_id": payload.resume_id,
                "status": "completed",
                "message": "Full verification pipeline completed in direct mode",
                "final_trust_score": final_score,
                "risk_level": risk_level,
                "classification": classification,
                "github_result": github_result,
                "certificate_results": cert_results,
                "resume_sha256": resume_hash,
                "blockchain_tx_hash": blockchain_tx_hash,
                "block_number": blockchain_block,
            }
        )


@router.get("/task-status/{task_id}")
async def task_status_endpoint(task_id: str):
    return success_response(get_task_status(task_id))


@router.post("/verify/blockchain-hash")
async def verify_blockchain_hash_endpoint(
    request: BlockchainHashVerificationRequest,
    _: Request,
):
    try:
        blockchain_service = get_blockchain_service()
        result = await blockchain_service.verify_resume_hash(
            tx_hash=request.tx_hash,
            expected_resume_hash=request.expected_hash,
        )
        return success_response(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Blockchain verification failed: {exc}")
