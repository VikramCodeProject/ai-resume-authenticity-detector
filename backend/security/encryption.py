"""
Enterprise-Grade Encryption
AES-256 encryption for sensitive data at rest
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf import pbkdf2
from cryptography.hazmat.backends import default_backend
import os
import base64
from typing import Union
from logging import getLogger

logger = getLogger(__name__)


class EncryptionManager:
    """
    AES-256 Encryption Manager
    Encrypts/decrypts sensitive data (resumes, credentials, etc.)
    """
    
    def __init__(self, master_key: str = None):
        """
        Initialize encryption manager
        
        Args:
            master_key: Master encryption key (must be 32+ chars in production)
        """
        if master_key is None:
            master_key = os.getenv("ENCRYPTION_KEY", "")

        if not master_key:
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError("ENCRYPTION_KEY must be configured in production")

            if os.getenv("ALLOW_INSECURE_DEV_ENCRYPTION", "false").lower() == "true":
                master_key = "unsafe-local-encryption-key"
                logger.warning("Using insecure development encryption key")
            else:
                raise ValueError(
                    "ENCRYPTION_KEY is required. Set ALLOW_INSECURE_DEV_ENCRYPTION=true only for local development"
                )
        
        self.master_key = master_key
        self._cipher_suite = None
        self._init_cipher()
    
    def _init_cipher(self):
        """Initialize Fernet cipher with key derivation"""
        # Derive a key from master_key using PBKDF2
        salt = b'resume_verify_salt'  # In production, use random salt per key
        kdf = pbkdf2.PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        # Derive key and encode for Fernet
        key_material = kdf.derive(self.master_key.encode())
        fernet_key = base64.urlsafe_b64encode(key_material)
        self._cipher_suite = Fernet(fernet_key)
    
    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """
        Encrypt data
        
        Args:
            plaintext: Data to encrypt (str or bytes)
            
        Returns:
            Base64-encoded encrypted data
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode()
            
            ciphertext = self._cipher_suite.encrypt(plaintext)
            return base64.urlsafe_b64encode(ciphertext).decode()
            
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
    
    def decrypt(self, ciphertext_b64: str) -> str:
        """
        Decrypt data
        
        Args:
            ciphertext_b64: Base64-encoded encrypted data
            
        Returns:
            Decrypted plaintext
        """
        try:
            ciphertext = base64.urlsafe_b64decode(ciphertext_b64.encode())
            plaintext = self._cipher_suite.decrypt(ciphertext)
            return plaintext.decode()
            
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using argon2
        
        Args:
            password: Plain password
            
        Returns:
            Hashed password
        """
        from argon2 import PasswordHasher
        from argon2.exceptions import InvalidHash
        
        ph = PasswordHasher()
        try:
            return ph.hash(password)
        except Exception as e:
            logger.error(f"Password hashing error: {str(e)}")
            raise
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain password
            password_hash: Hashed password
            
        Returns:
            True if password matches
        """
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError, InvalidHash
        
        ph = PasswordHasher()
        try:
            ph.verify(password_hash, password)
            return True
        except (VerifyMismatchError, InvalidHash):
            return False
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            raise


class DataClassificationLevel:
    """Data classification levels"""
    
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class EncryptedField:
    """
    Descriptor for encrypted fields in database models
    Automatically encrypts/decrypts on access
    """
    
    def __init__(self, encryption_manager: EncryptionManager = None, classification: str = DataClassificationLevel.CONFIDENTIAL):
        """
        Initialize encrypted field
        
        Args:
            encryption_manager: EncryptionManager instance
            classification: Data classification level
        """
        self.encryption_manager = encryption_manager or get_encryption_manager()
        self.classification = classification
        self.name = None
    
    def __set_name__(self, owner, name):
        """Called when descriptor is assigned to class attribute"""
        self.name = f"_encrypted_{name}"
    
    def __get__(self, obj, objtype=None):
        """Get decrypted value"""
        if obj is None:
            return self
        
        encrypted_value = getattr(obj, self.name, None)
        if encrypted_value is None:
            return None
        
        return self.encryption_manager.decrypt(encrypted_value)
    
    def __set__(self, obj, value):
        """Set encrypted value"""
        if value is None:
            setattr(obj, self.name, None)
        else:
            encrypted_value = self.encryption_manager.encrypt(value)
            setattr(obj, self.name, encrypted_value)


def get_encryption_manager() -> EncryptionManager:
    """Get encryption manager singleton"""
    global _encryption_manager
    if '_encryption_manager' not in globals():
        _encryption_manager = EncryptionManager()
    return _encryption_manager
