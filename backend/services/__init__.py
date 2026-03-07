"""
Services Module
Enterprise verification services for resume authenticity platform
"""

import logging

logger = logging.getLogger(__name__)

# Optional services - graceful degradation
try:
    from .github_service import GitHubVerificationService, get_github_service
except Exception as exc:
    logger.warning("GitHub service disabled: %s", exc)
    class GitHubVerificationService:  # type: ignore[no-redef]
        """Fallback placeholder"""
    def get_github_service():  # type: ignore[no-redef]
        raise RuntimeError("GitHub service unavailable")

try:
    from .llm_reasoning import LLMReasoningService, get_llm_service
except Exception as exc:
    logger.warning("LLM service disabled: %s", exc)
    class LLMReasoningService:  # type: ignore[no-redef]
        """Fallback placeholder"""
    def get_llm_service():  # type: ignore[no-redef]
        raise RuntimeError("LLM service unavailable")

try:
    from .blockchain_service import BlockchainVerificationService, get_blockchain_service
except Exception as exc:
    logger.warning("Blockchain service disabled: %s", exc)
    class BlockchainVerificationService:  # type: ignore[no-redef]
        """Fallback placeholder"""
    def get_blockchain_service():  # type: ignore[no-redef]
        raise RuntimeError("Blockchain service unavailable")

try:
    from .ocr_service import CertificateOCRService, get_ocr_service
except Exception as exc:
    logger.warning("OCR service disabled: %s", exc)

    class CertificateOCRService:  # type: ignore[no-redef]
        """Fallback OCR service placeholder when dependencies are unavailable."""

    def get_ocr_service():  # type: ignore[no-redef]
        raise RuntimeError(
            "OCR service is unavailable because OpenCV/NumPy dependencies failed to load. "
            "Install compatible versions to enable OCR endpoints."
        )

try:
    from .deepfake_detector import DeepfakeDetector, get_deepfake_detector
except Exception as exc:
    logger.warning("Deepfake detector disabled: %s", exc)

    class DeepfakeDetector:  # type: ignore[no-redef]
        """Fallback deepfake service placeholder when dependencies are unavailable."""

    def get_deepfake_detector():  # type: ignore[no-redef]
        raise RuntimeError(
            "Deepfake detector is unavailable because optional ML dependencies failed to load. "
            "Install compatible spaCy/typer versions to enable deepfake endpoints."
        )

__all__ = [
    'GitHubVerificationService',
    'get_github_service',
    'CertificateOCRService',
    'get_ocr_service',
    'LLMReasoningService',
    'get_llm_service',
    'DeepfakeDetector',
    'get_deepfake_detector',
    'BlockchainVerificationService',
    'get_blockchain_service',
]
