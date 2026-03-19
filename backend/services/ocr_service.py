"""
OCR Certificate Verification Service
Extract and validate certificate authenticity using OCR and NLP

Enterprise Features:
- Multi-OCR engine support (Tesseract + EasyOCR)
- Image preprocessing for accuracy
- Entity extraction with NLP
- Issuer whitelist validation
- Duplicate detection
- Tamper detection
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re
from pathlib import Path
import hashlib
import json
from difflib import SequenceMatcher

# Image processing
from PIL import Image
import cv2
import numpy as np

# OCR engines
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("easyocr not available")

# NLP for entity extraction
import spacy
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

_SEEN_IMAGE_HASHES: set[str] = set()


class CertificateOCRService:
    """
    Certificate verification using OCR and validation
    
    Workflow:
    1. Image preprocessing
    2. OCR text extraction (Tesseract or EasyOCR)
    3. Entity extraction (name, issuer, date, ID)
    4. Authenticity validation
    5. Duplicate detection
    """
    
    # Trusted certificate issuers whitelist
    TRUSTED_ISSUERS = {
        'coursera', 'udemy', 'edx', 'linkedin learning', 'pluralsight',
        'aws', 'amazon web services', 'microsoft', 'google', 'oracle',
        'cisco', 'comptia', 'ibm', 'red hat', 'vmware',
        'pmi', 'scrum alliance', 'safe', 'iiba', 'isaca',
        'stanford', 'mit', 'harvard', 'berkeley', 'oxford',
        'udacity', 'datacamp', 'kaggle', 'hubspot', 'salesforce'
    }
    
    def __init__(self, database_client=None, use_easyocr: bool = False):
        """
        Initialize OCR service
        
        Args:
            database_client: Database for duplicate detection
            use_easyocr: Use EasyOCR instead of Tesseract
        """
        self.database = database_client
        self.use_easyocr = use_easyocr and EASYOCR_AVAILABLE
        
        # Initialize OCR engine
        if self.use_easyocr:
            logger.info("Initializing EasyOCR...")
            self.reader = easyocr.Reader(['en'])
        elif not TESSERACT_AVAILABLE:
            raise RuntimeError("No OCR engine available. Install pytesseract or easyocr")
        
        # Load NLP model for entity extraction
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            logger.warning("spaCy model not found. Some features disabled.")
            self.nlp = None
        
        logger.info(f"OCR service initialized (engine: {'EasyOCR' if self.use_easyocr else 'Tesseract'})")
    
    async def verify_certificate(
        self,
        image_path: str,
        expected_name: Optional[str] = None,
        resume_id: Optional[str] = None
    ) -> Dict:
        """
        Complete certificate verification workflow
        
        Args:
            image_path: Path to certificate image
            expected_name: Expected candidate name from resume
            resume_id: Resume ID for duplicate detection
        
        Returns:
            Verification report with authenticity score
        """
        try:
            # 1. Preprocess image
            logger.info(f"Processing certificate: {image_path}")
            preprocessed_image = self._preprocess_image(image_path)
            
            # 2. Extract text with OCR
            extracted_text = self._extract_text_ocr(preprocessed_image)

            image_sha256 = self._compute_image_hash(image_path)
            
            if not extracted_text or len(extracted_text) < 10:
                return self._error_response("Failed to extract meaningful text from certificate")
            
            # 3. Extract entities (name, issuer, date, ID)
            entities = self._extract_entities(extracted_text, expected_name)
            
            # 4. Validate certificate
            validation_results = self._validate_certificate(entities, extracted_text)
            if expected_name:
                validation_results["name_match_score"] = self._name_match_score(
                    expected_name,
                    entities.get("name"),
                    extracted_text,
                )
            
            # 5. Check for duplicates
            duplicate_check = await self._check_duplicate(entities, resume_id)
            duplicate_check["image_hash"] = image_sha256
            duplicate_check["seen_image_hash"] = image_sha256 in _SEEN_IMAGE_HASHES
            _SEEN_IMAGE_HASHES.add(image_sha256)
            
            # 6. Detect tampering
            tamper_score = self._detect_tampering(image_path, extracted_text)
            
            # 7. Compute authenticity score
            authenticity_score = self._compute_authenticity_score(
                validation_results,
                duplicate_check,
                tamper_score,
                entities
            )
            
            # Build response
            result = {
                'certificate_valid': authenticity_score['is_authentic'],
                'authenticity_score': authenticity_score['total_score'],
                'risk_level': authenticity_score['risk_level'],
                'extracted_data': {
                    'full_text': extracted_text[:500],  # First 500 chars
                    'candidate_name': entities.get('name'),
                    'issuer': entities.get('issuer'),
                    'issue_date': entities.get('date'),
                    'certificate_id': entities.get('certificate_id'),
                    'course_name': entities.get('course_name')
                },
                'validation_checks': validation_results,
                'duplicate_detected': duplicate_check['is_duplicate'],
                'tamper_detection': tamper_score,
                'recommendations': self._generate_recommendations(
                    authenticity_score,
                    validation_results,
                    duplicate_check
                ),
                'verified_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Certificate verification complete: score={authenticity_score['total_score']:.2f}")
            return result
            
        except Exception as e:
            logger.exception(f"Certificate verification error: {str(e)}")
            return self._error_response(f"Verification failed: {str(e)}")
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy
        
        Steps:
        - Convert to grayscale
        - Denoise
        - Threshold/binarize
        - Deskew
        """
        # Load image
        img = cv2.imread(image_path)
        
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 
            2
        )
        
        # Deskew (straighten)
        angle = self._detect_skew(binary)
        if abs(angle) > 0.5:  # Only deskew if necessary
            binary = self._rotate_image(binary, angle)
        
        return binary
    
    def _detect_skew(self, image: np.ndarray) -> float:
        """Detect image skew angle"""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) < 10:
            return 0.0
        
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = 90 + angle
        
        return -angle
    
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by angle"""
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, 
            M, 
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
    
    def _extract_text_ocr(self, image: np.ndarray) -> str:
        """Extract text using OCR engine"""
        if self.use_easyocr:
            # EasyOCR
            results = self.reader.readtext(image)
            text = ' '.join([result[1] for result in results])
        else:
            # Tesseract
            text = pytesseract.image_to_string(image, config='--psm 6')
        
        # Clean text
        text = self._clean_text(text)
        
        logger.debug(f"Extracted text: {text[:100]}...")
        return text

    def _compute_image_hash(self, image_path: str) -> str:
        path = Path(image_path)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _name_match_score(self, expected_name: str, extracted_name: Optional[str], full_text: str) -> float:
        expected = (expected_name or "").strip().lower()
        if not expected:
            return 0.0

        candidates = []
        if extracted_name:
            candidates.append(extracted_name.lower())
        candidates.append(full_text.lower())
        return max(SequenceMatcher(None, expected, c).ratio() for c in candidates)
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-.,:()/]', '', text)
        return text.strip()
    
    def _extract_entities(self, text: str, expected_name: Optional[str] = None) -> Dict:
        """
        Extract key entities from certificate text
        
        Entities:
        - Name
        - Issuer
        - Date
        - Certificate ID
        - Course name
        """
        entities = {}
        
        # Extract name
        entities['name'] = self._extract_name(text, expected_name)
        
        # Extract issuer
        entities['issuer'] = self._extract_issuer(text)
        
        # Extract date
        entities['date'] = self._extract_date(text)
        
        # Extract certificate ID
        entities['certificate_id'] = self._extract_certificate_id(text)
        
        # Extract course/certificate name
        entities['course_name'] = self._extract_course_name(text)
        
        return entities
    
    def _extract_name(self, text: str, expected_name: Optional[str] = None) -> Optional[str]:
        """Extract candidate name"""
        # Try common patterns
        patterns = [
            r'(?:is awarded to|presented to|this certifies that)\s+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'Name:\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+has',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # Use spaCy if available
        if self.nlp:
            doc = self.nlp(text[:500])  # First 500 chars
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    return ent.text
        
        # Check if expected name appears in text
        if expected_name and expected_name.lower() in text.lower():
            return expected_name
        
        return None
    
    def _extract_issuer(self, text: str) -> Optional[str]:
        """Extract certificate issuer"""
        # Check for known issuers
        text_lower = text.lower()
        
        for issuer in self.TRUSTED_ISSUERS:
            if issuer in text_lower:
                return issuer.title()
        
        # Try common patterns
        patterns = [
            r'(?:issued by|from|by)\s+([A-Z][a-zA-Z\s]+(?:University|Institute|Academy|School|Learning|Education|Inc\.|LLC|Corp))',
            r'([A-Z][a-zA-Z\s]+(?:University|Institute|Academy|School))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                issuer = match.group(1).strip()
                if len(issuer) > 3:
                    return issuer
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract issue date"""
        # Try common date patterns
        date_patterns = [
            r'(?:issued on|date|dated|awarded on)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_obj = date_parser.parse(match.group(1))
                    return date_obj.strftime('%Y-%m-%d')
                except:
                    pass
        
        # Try fuzzy date parsing
        try:
            date_obj = date_parser.parse(text[:200], fuzzy=True)
            if date_obj.year > 2000 and date_obj.year <= datetime.now().year:
                return date_obj.strftime('%Y-%m-%d')
        except:
            pass
        
        return None
    
    def _extract_certificate_id(self, text: str) -> Optional[str]:
        """Extract certificate ID"""
        patterns = [
            r'(?:Certificate|Cert|ID|Number|No\.?)[:\s]+([A-Z0-9\-]{6,20})',
            r'#([A-Z0-9\-]{6,20})',
            r'\b([A-Z]{2,4}\-\d{4,10})\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cert_id = match.group(1).strip()
                if len(cert_id) >= 6:
                    return cert_id
        
        return None
    
    def _extract_course_name(self, text: str) -> Optional[str]:
        """Extract course/certificate name"""
        patterns = [
            r'Certificate (?:of|in)\s+([A-Za-z\s]+(?:Engineering|Science|Management|Development|Design|Analysis))',
            r'(?:completed|finished)\s+([A-Za-z\s]+(?:Course|Program|Training|Certification))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                course = match.group(1).strip()
                if len(course) > 5:
                    return course
        
        return None
    
    def _validate_certificate(self, entities: Dict, full_text: str) -> Dict:
        """Validate certificate data"""
        checks = {}
        
        # 1. Name validation
        checks['has_name'] = entities.get('name') is not None
        
        # 2. Issuer validation
        issuer = entities.get('issuer')
        checks['has_issuer'] = issuer is not None
        checks['trusted_issuer'] = (
            issuer.lower() in self.TRUSTED_ISSUERS 
            if issuer else False
        )
        
        # 3. Date validation
        date_str = entities.get('date')
        checks['has_date'] = date_str is not None
        checks['valid_date'] = False
        
        if date_str:
            try:
                cert_date = datetime.strptime(date_str, '%Y-%m-%d')
                now = datetime.now()
                
                # Check if date is reasonable (not in future, not too old)
                checks['valid_date'] = (
                    cert_date <= now and 
                    cert_date >= datetime(2000, 1, 1)
                )
            except:
                pass
        
        # 4. Certificate ID validation
        checks['has_certificate_id'] = entities.get('certificate_id') is not None
        
        # 5. Content quality
        checks['sufficient_content'] = len(full_text) > 50
        checks['has_keywords'] = any(
            keyword in full_text.lower() 
            for keyword in ['certificate', 'certify', 'awarded', 'completed', 'achievement']
        )
        
        return checks
    
    async def _check_duplicate(
        self, 
        entities: Dict, 
        resume_id: Optional[str]
    ) -> Dict:
        """Check for duplicate certificates in database"""
        cert_id = entities.get('certificate_id')
        
        if not cert_id or not self.database:
            return {'is_duplicate': False, 'duplicate_count': 0}
        
        try:
            # Query database for matching certificate ID
            # This is a placeholder - implement actual DB query
            # duplicate_count = await self.database.certificates.count_documents({
            #     'certificate_id': cert_id,
            #     'resume_id': {'$ne': resume_id}
            # })
            
            duplicate_count = 0  # Placeholder
            
            return {
                'is_duplicate': duplicate_count > 0,
                'duplicate_count': duplicate_count
            }
        except Exception as e:
            logger.error(f"Duplicate check error: {e}")
            return {'is_duplicate': False, 'duplicate_count': 0}
    
    def _detect_tampering(self, image_path: str, extracted_text: str) -> Dict:
        """Detect potential image tampering"""
        # Load original image
        img = cv2.imread(image_path)
        
        tampering_indicators = {
            'font_inconsistency': False,
            'compression_artifacts': False,
            'suspicious_score': 0.0
        }
        
        # 1. Check for font inconsistencies (multiple fonts might indicate editing)
        # Simple heuristic: analyze text regions
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) > 100:  # Too many text regions
            tampering_indicators['font_inconsistency'] = True
            tampering_indicators['suspicious_score'] += 0.3
        
        # 2. Check for JPEG compression artifacts (re-saved images)
        # High variance in compression can indicate editing
        try:
            jpg_quality = self._estimate_jpeg_quality(img)
            if jpg_quality < 70:
                tampering_indicators['compression_artifacts'] = True
                tampering_indicators['suspicious_score'] += 0.2
        except:
            pass
        
        # 3. Check for suspicious patterns in text
        unusual_chars = len(re.findall(r'[^\x00-\x7F]', extracted_text))
        if unusual_chars > len(extracted_text) * 0.1:
            tampering_indicators['suspicious_score'] += 0.2
        
        # Normalize score
        tampering_indicators['suspicious_score'] = min(1.0, tampering_indicators['suspicious_score'])
        
        return tampering_indicators
    
    def _estimate_jpeg_quality(self, img: np.ndarray) -> int:
        """Estimate JPEG quality (0-100)"""
        # This is a simplified heuristic
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Higher variance = better quality
        quality = min(100, int(laplacian_var / 10))
        return quality
    
    def _compute_authenticity_score(
        self,
        validation_results: Dict,
        duplicate_check: Dict,
        tamper_score: Dict,
        entities: Dict
    ) -> Dict:
        """Compute overall authenticity score"""
        score = 100.0
        
        # Deduct points for missing/invalid data
        if not validation_results.get('has_name'):
            score -= 20
        if validation_results.get('name_match_score', 1.0) < 0.6:
            score -= 20
        if not validation_results.get('has_issuer'):
            score -= 15
        if not validation_results.get('trusted_issuer'):
            score -= 10
        if not validation_results.get('valid_date'):
            score -= 15
        if not validation_results.get('has_certificate_id'):
            score -= 10
        if not validation_results.get('has_keywords'):
            score -= 10
        
        # Deduct for duplicates
        if duplicate_check.get('is_duplicate'):
            score -= 30
        if duplicate_check.get('seen_image_hash'):
            score -= 15
        
        # Deduct for tampering
        tamper_score_value = tamper_score.get('suspicious_score', 0)
        score -= tamper_score_value * 20
        
        # Ensure score is in valid range
        score = max(0.0, min(100.0, score))
        
        # Determine risk level
        if score >= 80:
            risk_level = "Low"
            is_authentic = True
        elif score >= 60:
            risk_level = "Medium"
            is_authentic = True
        elif score >= 40:
            risk_level = "High"
            is_authentic = False
        else:
            risk_level = "Critical"
            is_authentic = False
        
        return {
            'total_score': round(score, 2),
            'is_authentic': is_authentic,
            'risk_level': risk_level
        }
    
    def _generate_recommendations(
        self,
        authenticity_score: Dict,
        validation_results: Dict,
        duplicate_check: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if not validation_results.get('trusted_issuer'):
            recommendations.append("Issuer not in trusted list - verify independently")
        
        if not validation_results.get('valid_date'):
            recommendations.append("Certificate date is invalid or missing")
        
        if duplicate_check.get('is_duplicate'):
            recommendations.append("⚠️ Certificate ID found in multiple resumes")
        
        if not validation_results.get('has_certificate_id'):
            recommendations.append("No certificate ID found - difficult to verify")
        
        if authenticity_score['total_score'] < 60:
            recommendations.append("LOW CONFIDENCE - Manual verification recommended")
        
        if not recommendations:
            recommendations.append("Certificate appears authentic")
        
        return recommendations
    
    def _error_response(self, error_message: str) -> Dict:
        """Generate error response"""
        return {
            'certificate_valid': False,
            'authenticity_score': 0.0,
            'risk_level': 'Critical',
            'error': error_message,
            'verified_at': datetime.utcnow().isoformat()
        }


# Singleton instance
_ocr_service: Optional[CertificateOCRService] = None

def get_ocr_service(
    database_client=None,
    use_easyocr: bool = False
) -> CertificateOCRService:
    """Get or create OCR service instance"""
    global _ocr_service
    
    if _ocr_service is None:
        _ocr_service = CertificateOCRService(database_client, use_easyocr)
    
    return _ocr_service
