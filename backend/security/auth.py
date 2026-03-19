"""
Enterprise JWT Authentication & RBAC
Role-Based Access Control with Token Management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel
from functools import lru_cache
import os
from logging import getLogger

logger = getLogger(__name__)


class UserRole(str, Enum):
    """Enterprise user roles"""
    
    ADMIN = "admin"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"
    AUDITOR = "auditor"
    ANALYST = "analyst"


class TokenType(str, Enum):
    """Token types"""
    
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """JWT Token Payload Structure"""
    
    sub: str  # user_id
    email: str
    role: UserRole
    token_type: TokenType
    exp: datetime
    iat: datetime
    jti: str  # Unique token ID for revocation


class UserCredentials(BaseModel):
    """User credentials for authentication"""
    
    email: str
    password: str


class TokenResponse(BaseModel):
    """Token response structure"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    role: UserRole


class JWTManager:
    """
    Enterprise JWT Manager
    Handles token generation, validation, and refresh
    """
    
    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7
    ):
        """
        Initialize JWT Manager
        
        Args:
            secret_key: JWT signing secret (must be >=32 chars in production)
            algorithm: JWT algorithm
            access_token_expire_minutes: Access token TTL
            refresh_token_expire_days: Refresh token TTL
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET", "")
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)
        self._revoked_jtis: set[str] = set()
        self._allow_insecure_dev_secret = os.getenv("ALLOW_INSECURE_DEV_JWT", "false").lower() == "true"

        if not self.secret_key:
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError("JWT_SECRET must be configured in production")
            if self._allow_insecure_dev_secret:
                self.secret_key = "unsafe-local-development-secret"
                logger.warning("Using insecure development JWT secret")
            else:
                raise ValueError("JWT_SECRET is required. Set ALLOW_INSECURE_DEV_JWT=true only for local development")
        
        # Validate secret in production
        if os.getenv("ENVIRONMENT") == "production" and len(self.secret_key) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: UserRole,
        jti: str = None
    ) -> str:
        """
        Create JWT access token
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            jti: JWT ID for logout tracking
            
        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        expires = now + self.access_token_expire
        
        payload = TokenPayload(
            sub=user_id,
            email=email,
            role=role,
            token_type=TokenType.ACCESS,
            exp=expires,
            iat=now,
            jti=jti or self._generate_jti()
        )
        
        token = jwt.encode(
            payload.model_dump(mode="json"),
            self.secret_key,
            algorithm=self.algorithm
        )
        
        logger.info(f"Access token created for user {user_id}")
        return token
    
    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        role: UserRole,
        jti: str = None
    ) -> str:
        """
        Create JWT refresh token
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            jti: JWT ID
            
        Returns:
            JWT refresh token string
        """
        now = datetime.now(timezone.utc)
        expires = now + self.refresh_token_expire
        
        payload = TokenPayload(
            sub=user_id,
            email=email,
            role=role,
            token_type=TokenType.REFRESH,
            exp=expires,
            iat=now,
            jti=jti or self._generate_jti()
        )
        
        token = jwt.encode(
            payload.model_dump(mode="json"),
            self.secret_key,
            algorithm=self.algorithm
        )
        
        logger.info(f"Refresh token created for user {user_id}")
        return token
    
    def create_token_pair(
        self,
        user_id: str,
        email: str,
        role: UserRole
    ) -> TokenResponse:
        """
        Create access + refresh token pair
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            
        Returns:
            TokenResponse with both tokens
        """
        jti_id = self._generate_jti()
        
        access_token = self.create_access_token(user_id, email, role, jti_id)
        refresh_token = self.create_refresh_token(user_id, email, role, jti_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.access_token_expire.total_seconds()),
            user_id=user_id,
            email=email,
            role=role
        )
    
    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded TokenPayload
            
        Raises:
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            token_data = TokenPayload(**payload)
            if token_data.jti in self._revoked_jtis:
                raise InvalidTokenError("Token has been revoked")
            logger.debug(f"Token verified for user {token_data.sub}")
            return token_data
            
        except InvalidTokenError as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise InvalidTokenError("Invalid or expired token") from e
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token
            
        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        payload = self.verify_token(refresh_token)
        
        if payload.token_type != TokenType.REFRESH:
            raise InvalidTokenError("Not a refresh token")
        
        # Create new access token with same JTI for tracking
        access_token = self.create_access_token(
            payload.sub,
            payload.email,
            payload.role,
            payload.jti
        )
        
        logger.info(f"Access token refreshed for user {payload.sub}")
        return access_token
    
    def revoke_token(self, jti: str) -> None:
        """
        Revoke token by JTI (would use Redis in production)
        
        Args:
            jti: JWT ID to revoke
        """
        self._revoked_jtis.add(jti)
        logger.info(f"Token {jti} marked for revocation")
    
    @staticmethod
    def _generate_jti() -> str:
        """Generate unique JWT ID"""
        import uuid
        return str(uuid.uuid4())


class RBACManager:
    """
    Role-Based Access Control Manager
    Manages permissions per role
    """
    
    # Define permissions per role
    ROLE_PERMISSIONS: Dict[UserRole, List[str]] = {
        UserRole.ADMIN: [
            "read:resume",
            "write:resume",
            "delete:resume",
            "read:user",
            "write:user",
            "delete:user",
            "read:verification",
            "write:verification",
            "manage:system",
            "view:audit",
            "export:data"
        ],
        UserRole.RECRUITER: [
            "read:resume",
            "write:resume",
            "read:verification",
            "view:reports",
            "export:data"
        ],
        UserRole.CANDIDATE: [
            "read:resume:own",
            "write:resume:own",
            "read:verification:own",
            "view:report:own"
        ],
        UserRole.AUDITOR: [
            "read:resume",
            "read:verification",
            "view:audit",
            "export:audit"
        ],
        UserRole.ANALYST: [
            "read:resume",
            "read:verification",
            "view:reports",
            "export:data"
        ]
    }
    
    @classmethod
    def has_permission(cls, role: UserRole, permission: str) -> bool:
        """
        Check if role has permission
        
        Args:
            role: User role
            permission: Permission to check
            
        Returns:
            True if role has permission
        """
        return permission in cls.ROLE_PERMISSIONS.get(role, [])
    
    @classmethod
    def get_role_permissions(cls, role: UserRole) -> List[str]:
        """
        Get all permissions for a role
        
        Args:
            role: User role
            
        Returns:
            List of permissions
        """
        return cls.ROLE_PERMISSIONS.get(role, [])
    
    @classmethod
    def require_permission(cls, required_permission: str):
        """
        Decorator to require specific permission
        
        Usage:
            @require_permission("write:resume")
            async def update_resume(...): ...
        """
        def decorator(func):
            async def wrapper(current_user: TokenPayload, *args, **kwargs):
                if not cls.has_permission(current_user.role, required_permission):
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission '{required_permission}' required"
                    )
                return await func(current_user, *args, **kwargs)
            return wrapper
        return decorator


@lru_cache()
def get_jwt_manager() -> JWTManager:
    """Get JWT manager singleton"""
    return JWTManager()


@lru_cache()
def get_rbac_manager() -> RBACManager:
    """Get RBAC manager singleton"""
    return RBACManager()
