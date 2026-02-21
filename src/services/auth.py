"""Authentication service for user management and authentication"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from loguru import logger

from src.models import User
from src.schemas import UserCreate, UserLogin, PasswordChange, UserResponse
from src.security import SecurityUtils, PasswordManager
from config.settings import get_settings

settings = get_settings()


class UserNotFoundError(Exception):
    """Raised when user is not found"""
    pass


class InvalidCredentialsError(Exception):
    """Raised when credentials are invalid"""
    pass


class UserAlreadyExistsError(Exception):
    """Raised when user already exists"""
    pass


class AuthenticationService:
    """Handle all authentication operations"""
    
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """
        Register a new user
        
        Args:
            db: Database session
            user_data: User registration data
            
        Returns:
            Created User object
            
        Raises:
            UserAlreadyExistsError: If user with email or username already exists
        """
        # Check if user already exists
        existing_user = db.query(User).filter(
            (func.lower(User.email) == func.lower(user_data.email)) |
            (func.lower(User.username) == func.lower(user_data.username))
        ).first()
        
        if existing_user:
            logger.warning(f"Registration attempt for existing user: {user_data.email}")
            raise UserAlreadyExistsError(
                f"User with email {user_data.email} or username {user_data.username} already exists"
            )
        
        # Create new user
        user_id = str(uuid.uuid4())  # Explicit string conversion
        new_user = User(
            id=user_id,  # Pass the string directly
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name or user_data.username,
            hashed_password=PasswordManager.hash_password(user_data.password),
            role="user",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logger.info(f"User registered successfully: {new_user.username}")
            return new_user
        except Exception as e:
            db.rollback()
            logger.error(f"Registration error: {str(e)}")
            raise
    
    @staticmethod
    def authenticate_user(db: Session, credentials: UserLogin) -> User:
        """
        Authenticate user with username/email and password
        
        Args:
            db: Database session
            credentials: Login credentials
            
        Returns:
            Authenticated User object
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        # Find user by username or email (case-insensitive)
        user = db.query(User).filter(
            (func.lower(User.username) == func.lower(credentials.username)) |
            (func.lower(User.email) == func.lower(credentials.username))
        ).first()
        
        if not user:
            logger.warning(f"Login attempt with non-existent user: {credentials.username}")
            raise InvalidCredentialsError("Invalid username or password")
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.username}")
            raise InvalidCredentialsError("User account is inactive")
        
        if not PasswordManager.verify_password(credentials.password, user.hashed_password):
            logger.warning(f"Failed login attempt for user: {user.username}")
            raise InvalidCredentialsError("Invalid username or password")
        
        logger.info(f"User authenticated successfully: {user.username}")
        return user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            db: Database session
            user_id: User UUID
            
        Returns:
            User object or None if not found
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """
        Get user by username (case-insensitive)
        
        Args:
            db: Database session
            username: Username to search for
            
        Returns:
            User object or None if not found
        """
        return db.query(User).filter(
            func.lower(User.username) == func.lower(username)
        ).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Get user by email (case-insensitive)
        
        Args:
            db: Database session
            email: Email to search for
            
        Returns:
            User object or None if not found
        """
        return db.query(User).filter(
            func.lower(User.email) == func.lower(email)
        ).first()
    
    @staticmethod
    def change_password(db: Session, user: User, password_data: PasswordChange) -> User:
        """
        Change user password
        
        Args:
            db: Database session
            user: User object
            password_data: Password change data with old and new passwords
            
        Returns:
            Updated User object
            
        Raises:
            InvalidCredentialsError: If old password is incorrect
        """
        if not PasswordManager.verify_password(password_data.old_password, user.hashed_password):
            logger.warning(f"Failed password change attempt for user: {user.username}")
            raise InvalidCredentialsError("Current password is incorrect")
        
        user.hashed_password = PasswordManager.hash_password(password_data.new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        try:
            db.commit()
            db.refresh(user)
            logger.info(f"Password changed successfully for user: {user.username}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Password change error: {str(e)}")
            raise
    
    @staticmethod
    def deactivate_user(db: Session, user: User) -> User:
        """
        Deactivate a user account
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            Updated User object
        """
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        
        try:
            db.commit()
            db.refresh(user)
            logger.info(f"User deactivated: {user.username}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"User deactivation error: {str(e)}")
            raise
    
    @staticmethod
    def activate_user(db: Session, user: User) -> User:
        """
        Activate a user account
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            Updated User object
        """
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        
        try:
            db.commit()
            db.refresh(user)
            logger.info(f"User activated: {user.username}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"User activation error: {str(e)}")
            raise


class TokenService:
    """Handle token generation and refresh logic"""
    
    @staticmethod
    def generate_tokens(user: User) -> tuple[str, str, datetime, datetime]:
        """
        Generate access and refresh tokens for a user
        
        Args:
            user: User object
            
        Returns:
            Tuple of (access_token, refresh_token, access_expires, refresh_expires)
        """
        access_token, access_expires = SecurityUtils.create_access_token(str(user.id))
        refresh_token, refresh_expires = SecurityUtils.create_refresh_token(str(user.id))
        
        logger.debug(f"Tokens generated for user: {user.username}")
        return access_token, refresh_token, access_expires, refresh_expires
    
    @staticmethod
    def refresh_tokens(refresh_token: str) -> Optional[tuple[str, datetime]]:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, expiration) or None if refresh token invalid
        """
        payload = SecurityUtils.verify_refresh_token(refresh_token)
        
        if not payload:
            logger.warning("Refresh token verification failed")
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Refresh token missing user ID")
            return None
        
        access_token, access_expires = SecurityUtils.create_access_token(user_id)
        logger.debug(f"Token refreshed for user: {user_id}")
        return access_token, access_expires
