"""Security utilities for authentication and password management"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from loguru import logger
from config.settings import get_settings

# Password hashing context - using argon2 as primary, bcrypt as fallback
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4
)

settings = get_settings()


class PasswordManager:
    """Handle password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using argon2
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False


class TokenManager:
    """Handle JWT token creation and validation"""
    
    @staticmethod
    def create_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        token_type: str = "access"
    ) -> tuple[str, datetime]:
        """
        Create a JWT token
        
        Args:
            data: Data to encode in token
            expires_delta: Token expiration time
            token_type: Type of token (access, refresh)
            
        Returns:
            Tuple of (token, expiration_datetime)
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            if token_type == "access":
                expire = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.access_token_expire_minutes
                )
            else:  # refresh token
                expire = datetime.now(timezone.utc) + timedelta(days=7)
        
        to_encode.update({"exp": expire, "type": token_type})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                settings.secret_key,
                algorithm=settings.algorithm
            )
            logger.debug(f"Created {token_type} token for user {data.get('sub')}")
            return encoded_jwt, expire
        except Exception as e:
            logger.error(f"Token creation error: {str(e)}")
            raise
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (access, refresh)
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return None
            
            user_id: str = payload.get("sub")
            if user_id is None:
                logger.warning("Token missing 'sub' claim")
                return None
            
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
    
    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        """
        Extract user ID from a valid token
        
        Args:
            token: JWT token
            
        Returns:
            User ID or None if invalid
        """
        payload = TokenManager.verify_token(token)
        if payload:
            return payload.get("sub")
        return None


class SecurityUtils:
    """General security utilities"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return PasswordManager.hash_password(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password"""
        return PasswordManager.verify_password(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(user_id: str) -> tuple[str, datetime]:
        """Create an access token for a user"""
        return TokenManager.create_token(
            data={"sub": user_id},
            token_type="access"
        )
    
    @staticmethod
    def create_refresh_token(user_id: str) -> tuple[str, datetime]:
        """Create a refresh token for a user"""
        return TokenManager.create_token(
            data={"sub": user_id},
            token_type="refresh"
        )
    
    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify an access token"""
        return TokenManager.verify_token(token, token_type="access")
    
    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify a refresh token"""
        return TokenManager.verify_token(token, token_type="refresh")
