"""Pydantic schemas for authentication and user management"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    ANALYST = "analyst"
    TRADER = "trader"
    VIEWER = "viewer"
    USER = "user"


# ============ Request Schemas ============

class UserCreate(BaseModel):
    """User creation request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    
    @validator("username")
    def username_alphanumeric(cls, v):
        """Validate username contains only alphanumeric and underscores"""
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v


class UserLogin(BaseModel):
    """User login request"""
    username: str
    password: str


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str


class PasswordChange(BaseModel):
    """Password change request"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator("new_password")
    def password_strength(cls, v):
        """Validate password strength"""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ============ Response Schemas ============

class UserResponse(BaseModel):
    """User response (without sensitive data)"""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
    
    @validator('created_at', 'updated_at', pre=True)
    def convert_datetime(cls, v):
        """Convert datetime to ISO format string"""
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        return str(v)


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginResponse(BaseModel):
    """Login response with user data"""
    user: UserResponse
    tokens: TokenResponse


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    status: str = "success"
