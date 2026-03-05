"""
Services Module
Enterprise verification services for resume authenticity platform
"""

from .github_service import GitHubVerificationService, get_github_service
from .ocr_service import CertificateOCRService, get_ocr_service
from .llm_reasoning import LLMReasoningService, get_llm_service
from .deepfake_detector import DeepfakeDetector, get_deepfake_detector
from .blockchain_service import BlockchainVerificationService, get_blockchain_service

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
