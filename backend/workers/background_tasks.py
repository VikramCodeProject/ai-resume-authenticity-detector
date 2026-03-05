import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery import Celery
from celery.result import AsyncResult

from monitoring.metrics import ai_inference_time_seconds
from services import get_deepfake_detector, get_github_service, get_llm_service, get_ocr_service
from services.blockchain_service import get_blockchain_service
from utils.logger import get_logger


logger = get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

celery_app = Celery("resume_verifier_workers", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(bind=True, name="workers.verify_resume_ai")
def verify_resume_ai(self, resume_id: str, file_path: str) -> Dict[str, Any]:
    logger.info("Resume AI analysis started", extra={"resume_id": resume_id})
    started = time.perf_counter()
    with ai_inference_time_seconds.labels(operation="resume_ai_analysis").time():
        try:
            from ml_engine.pipeline import ClaimExtractor, ResumeParser

            parser = ResumeParser()
            text = parser.parse(file_path)
            claims = ClaimExtractor().extract(text)
            score = max(20.0, min(95.0, 40.0 + min(len(claims), 11) * 5.0))
            latency_ms = round((time.perf_counter() - started) * 1000, 2)

            logger.info(
                "AI inference results",
                extra={
                    "service": "resume-verifier",
                    "endpoint": "/verify/resume",
                    "status": "success",
                    "latency_ms": latency_ms,
                    "resume_id": resume_id,
                    "claims_count": len(claims),
                    "score": score,
                },
            )

            return {
                "resume_id": resume_id,
                "status": "completed",
                "claims_count": len(claims),
                "trust_score": score,
                "completed_at": datetime.utcnow().isoformat(),
            }
        except Exception:
            logger.exception("Resume AI analysis failed", extra={"resume_id": resume_id})
            raise


@celery_app.task(bind=True, name="workers.verify_github")
def verify_github(self, username: str, claimed_skills: Optional[List[str]] = None) -> Dict[str, Any]:
    logger.info("GitHub verification started", extra={"username": username})
    with ai_inference_time_seconds.labels(operation="github_scoring").time():
        try:
            service = get_github_service(api_token=os.getenv("GITHUB_API_KEY", ""))
            result = asyncio.run(service.verify_profile(username=username, claimed_skills=claimed_skills or []))
            logger.info("GitHub verification complete", extra={"username": username, "status": "success"})
            return result
        except Exception:
            logger.exception("GitHub verification failed", extra={"username": username})
            raise


@celery_app.task(bind=True, name="workers.verify_certificate")
def verify_certificate(self, image_path: str, expected_name: Optional[str] = None, resume_id: Optional[str] = None) -> Dict[str, Any]:
    logger.info("Certificate verification started", extra={"image_path": image_path})
    with ai_inference_time_seconds.labels(operation="ocr_processing").time():
        try:
            service = get_ocr_service()
            result = asyncio.run(service.verify_certificate(image_path=image_path, expected_name=expected_name, resume_id=resume_id))
            logger.info("Certificate verification complete", extra={"status": "success", "resume_id": resume_id})
            return result
        except Exception:
            logger.exception("OCR processing failed", extra={"image_path": image_path})
            raise


@celery_app.task(bind=True, name="workers.verify_full")
def verify_full(
    self,
    resume_id: str,
    github_username: Optional[str] = None,
    certificate_image_paths: Optional[List[str]] = None,
    claimed_skills: Optional[List[str]] = None,
    resume_text: Optional[str] = None,
) -> Dict[str, Any]:
    logger.info("Full verification started", extra={"resume_id": resume_id})
    certificate_image_paths = certificate_image_paths or []
    claimed_skills = claimed_skills or []

    github_result = None
    certificate_results = []
    deepfake_result = None

    if github_username:
        github_result = verify_github.apply(args=[github_username, claimed_skills]).get(timeout=300)

    if certificate_image_paths:
        for image_path in certificate_image_paths:
            cert_result = verify_certificate.apply(args=[image_path, None, resume_id]).get(timeout=300)
            certificate_results.append(cert_result)

    if resume_text:
        with ai_inference_time_seconds.labels(operation="deepfake_detection").time():
            detector = get_deepfake_detector(use_perplexity=False)
            deepfake_result = asyncio.run(detector.analyze_resume_text(resume_text))

    llm_result = None
    with ai_inference_time_seconds.labels(operation="llm_reasoning").time():
        llm_service = get_llm_service(use_openai=False)
        llm_result = asyncio.run(
            llm_service.generate_verification_explanation(
                resume_data={
                    "name": resume_id,
                    "experience_years": 3,
                    "skills": claimed_skills,
                    "education": [],
                    "employment": [],
                },
                github_analysis=github_result,
                certificate_analysis=certificate_results[0] if certificate_results else None,
                deepfake_analysis=deepfake_result,
                ml_prediction=None,
                timeline_anomalies=[],
            )
        )

    final_score = llm_result.get("final_trust_score", 50.0) if llm_result else 50.0
    blockchain_payload = {"resume_id": resume_id, "score": final_score}
    blockchain_result = asyncio.run(get_blockchain_service().verify_claim_on_chain(blockchain_payload))

    result = {
        "resume_id": resume_id,
        "final_trust_score": final_score,
        "classification": "Verified" if final_score >= 75 else "Doubtful" if final_score >= 50 else "Fake",
        "github_analysis": github_result,
        "certificate_analysis": certificate_results,
        "deepfake_analysis": deepfake_result,
        "llm_explanation": llm_result,
        "blockchain": blockchain_result,
        "verified_at": datetime.utcnow().isoformat(),
        "status": "completed",
    }
    logger.info("Blockchain transaction", extra={"resume_id": resume_id, "status": blockchain_result.get("status")})
    return result


def get_task_status(task_id: str) -> Dict[str, Any]:
    task_result = AsyncResult(task_id, app=celery_app)
    payload: Dict[str, Any] = {
        "task_id": task_id,
        "status": task_result.status,
        "ready": task_result.ready(),
    }

    if task_result.successful():
        payload["result"] = task_result.result
    elif task_result.failed():
        payload["error"] = str(task_result.result)
    elif task_result.info:
        payload["meta"] = task_result.info

    return payload
