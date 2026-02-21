"""Authentication API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from src.database import get_db
from src.schemas import (
    UserCreate, UserLogin, TokenRefresh, PasswordChange,
    UserResponse, LoginResponse, TokenResponse, MessageResponse
)
from src.services.auth import (
    AuthenticationService, TokenService,
    UserAlreadyExistsError, InvalidCredentialsError
)
from src.middleware.rbac import get_current_user_id
from src.models import User

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        409: {"description": "Conflict - user already exists"},
    },
)


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password"
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> dict:
    """
    Register a new user
    
    - **username**: 3-50 characters, alphanumeric and underscores only
    - **email**: Valid email address
    - **password**: Minimum 8 characters, must include uppercase letter and digit
    - **full_name**: Optional full name
    
    Returns tokens for immediate authentication
    """
    try:
        # Register user
        new_user = AuthenticationService.register_user(db, user_data)
        
        # Generate tokens
        access_token, refresh_token, access_expires, refresh_expires = TokenService.generate_tokens(new_user)
        
        logger.info(f"User registered successfully: {new_user.username}")
        
        # Calculate expires_in using a safe method
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        expires_in = int((access_expires - now).total_seconds()) if hasattr(access_expires, 'timestamp') else 3600
        
        return {
            "user": UserResponse.from_orm(new_user),
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": expires_in
            }
        }
    except UserAlreadyExistsError as e:
        logger.warning(f"Registration failed - user exists: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate with username/email and password"
)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> dict:
    """
    Login with username or email and password
    
    - **username**: Username or email address
    - **password**: Account password
    
    Returns access and refresh tokens
    """
    try:
        # Authenticate user
        user = AuthenticationService.authenticate_user(db, credentials)
        
        # Generate tokens
        access_token, refresh_token, access_expires, refresh_expires = TokenService.generate_tokens(user)
        
        logger.info(f"User logged in: {user.username}")
        
        # Calculate expires_in using a safe method
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        expires_in = int((access_expires - now).total_seconds()) if hasattr(access_expires, 'timestamp') else 3600
        
        return {
            "user": UserResponse.from_orm(user),
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": expires_in
            }
        }
    except InvalidCredentialsError as e:
        logger.warning(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate a new access token using a valid refresh token"
)
async def refresh_token(token_data: TokenRefresh) -> dict:
    """
    Refresh access token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token
    """
    result = TokenService.refresh_tokens(token_data.refresh_token)
    
    if not result:
        logger.warning("Token refresh failed - invalid refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    access_token, access_expires = result
    
    logger.debug("Access token refreshed successfully")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(access_expires.timestamp())
    }


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get the current authenticated user's information"
)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get current authenticated user information
    
    Requires valid access token in Authorization header
    """
    user = AuthenticationService.get_user_by_id(db, user_id)
    
    if not user:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change the current user's password"
)
async def change_password(
    password_data: PasswordChange,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Change current user's password
    
    - **old_password**: Current password
    - **new_password**: New password (min 8 chars, uppercase + digit required)
    
    Requires valid access token
    """
    try:
        user = AuthenticationService.get_user_by_id(db, user_id)
        
        if not user:
            logger.warning(f"User not found for password change: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        AuthenticationService.change_password(db, user, password_data)
        
        logger.info(f"Password changed for user: {user.username}")
        
        return {"message": "Password changed successfully"}
    except InvalidCredentialsError as e:
        logger.warning(f"Password change failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout the current user (token invalidation on client side)"
)
async def logout(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Logout current user
    
    Note: Token invalidation should be handled on the client side.
    This endpoint can be used to trigger server-side cleanup if needed.
    """
    logger.info(f"User logged out: {user_id}")
    return {"message": "Logged out successfully"}
