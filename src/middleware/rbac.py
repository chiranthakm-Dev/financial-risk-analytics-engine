"""Role-Based Access Control utilities and middleware"""

from typing import Optional, Set, List, Callable
from enum import Enum
from functools import wraps
from loguru import logger
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.security import SecurityUtils


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    ANALYST = "analyst"
    TRADER = "trader"
    VIEWER = "viewer"
    USER = "user"


class Permission(str, Enum):
    """System permissions"""
    # Data management
    UPLOAD_DATA = "upload_data"
    DELETE_DATA = "delete_data"
    VIEW_DATA = "view_data"
    EXPORT_DATA = "export_data"
    
    # Model management
    TRAIN_MODEL = "train_model"
    VIEW_MODEL = "view_model"
    DELETE_MODEL = "delete_model"
    
    # Forecasting
    CREATE_FORECAST = "create_forecast"
    VIEW_FORECAST = "view_forecast"
    DELETE_FORECAST = "delete_forecast"
    
    # Risk analytics
    VIEW_RISK_METRICS = "view_risk_metrics"
    RUN_RISK_ANALYSIS = "run_risk_analysis"
    VIEW_MONTE_CARLO = "view_monte_carlo"
    
    # Reporting
    VIEW_REPORTS = "view_reports"
    CREATE_REPORTS = "create_reports"
    DELETE_REPORTS = "delete_reports"
    
    # User management (admin only)
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOG = "view_audit_log"


class RolePermissionMap:
    """Map roles to permissions"""
    
    ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
        UserRole.ADMIN: set(Permission),  # Admin has all permissions
        UserRole.ANALYST: {
            Permission.UPLOAD_DATA,
            Permission.VIEW_DATA,
            Permission.EXPORT_DATA,
            Permission.TRAIN_MODEL,
            Permission.VIEW_MODEL,
            Permission.CREATE_FORECAST,
            Permission.VIEW_FORECAST,
            Permission.VIEW_RISK_METRICS,
            Permission.RUN_RISK_ANALYSIS,
            Permission.VIEW_MONTE_CARLO,
            Permission.VIEW_REPORTS,
            Permission.CREATE_REPORTS,
        },
        UserRole.TRADER: {
            Permission.VIEW_DATA,
            Permission.VIEW_FORECAST,
            Permission.VIEW_RISK_METRICS,
            Permission.VIEW_MONTE_CARLO,
            Permission.VIEW_REPORTS,
        },
        UserRole.VIEWER: {
            Permission.VIEW_DATA,
            Permission.VIEW_FORECAST,
            Permission.VIEW_RISK_METRICS,
            Permission.VIEW_REPORTS,
        },
        UserRole.USER: {
            Permission.VIEW_DATA,
            Permission.VIEW_REPORTS,
        },
    }
    
    @classmethod
    def has_permission(cls, role: str, permission: Permission) -> bool:
        """Check if role has permission"""
        try:
            role_enum = UserRole(role)
            return permission in cls.ROLE_PERMISSIONS.get(role_enum, set())
        except ValueError:
            logger.warning(f"Unknown role: {role}")
            return False
    
    @classmethod
    def get_role_permissions(cls, role: str) -> Set[Permission]:
        """Get all permissions for a role"""
        try:
            role_enum = UserRole(role)
            return cls.ROLE_PERMISSIONS.get(role_enum, set())
        except ValueError:
            return set()


security = HTTPBearer()


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extract and validate current user ID from JWT token
    
    Args:
        credentials: HTTP Bearer credentials (JWT token)
        
    Returns:
        User ID as string
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    user_id = SecurityUtils.verify_access_token(token)
    
    if not user_id:
        logger.warning("Invalid access token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str = user_id.get("sub")
    if not user_id_str:
        logger.warning("Token missing user ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id_str


def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator to require specific roles for an endpoint
    
    Args:
        allowed_roles: List of allowed role names
        
    Returns:
        Decorator function
        
    Example:
        @require_role("admin", "analyst")
        async def admin_endpoint(user_role: str = Depends(get_current_user_role)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, user_role: str = Depends(lambda: get_current_user_role()), **kwargs):
            if user_role not in allowed_roles:
                logger.warning(f"Role {user_role} not in allowed roles: {allowed_roles}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This operation requires one of the following roles: {', '.join(allowed_roles)}"
                )
            return await func(*args, user_role=user_role, **kwargs)
        return wrapper
    return decorator


def require_permission(*permissions: Permission) -> Callable:
    """
    Decorator to require specific permissions for an endpoint
    
    Args:
        permissions: List of required permissions
        
    Returns:
        Decorator function
        
    Example:
        @require_permission(Permission.UPLOAD_DATA, Permission.TRAIN_MODEL)
        async def protected_endpoint(user_role: str = Depends(get_current_user_role)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, user_role: str = Depends(lambda: get_current_user_role()), **kwargs):
            required_permissions = set(permissions)
            user_permissions = RolePermissionMap.get_role_permissions(user_role)
            
            if not required_permissions.issubset(user_permissions):
                missing_perms = required_permissions - user_permissions
                logger.warning(f"User with role {user_role} missing permissions: {missing_perms}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User lacks required permissions: {', '.join(str(p.value) for p in missing_perms)}"
                )
            return await func(*args, user_role=user_role, **kwargs)
        return wrapper
    return decorator


async def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract user role from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        User role as string
        
    Raises:
        HTTPException: If token is invalid
        
    Note:
        This is a simplified version. In production, you should fetch the role
        from the database using the user_id from the token.
    """
    token = credentials.credentials
    payload = SecurityUtils.verify_access_token(token)
    
    if not payload:
        logger.warning("Invalid access token for role extraction")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Note: In production, retrieve role from database
    # For now, we return a default role that should be fetched from the token
    # or database based on user_id
    role = payload.get("role", "user")
    return role


class RBACMiddleware:
    """Middleware for role-based access control"""
    
    @staticmethod
    def check_permission(user_role: str, required_permission: Permission) -> bool:
        """
        Check if user has required permission
        
        Args:
            user_role: User's role
            required_permission: Required permission
            
        Returns:
            True if user has permission, False otherwise
        """
        return RolePermissionMap.has_permission(user_role, required_permission)
    
    @staticmethod
    def get_role_description(role: str) -> str:
        """Get human-readable description of role"""
        descriptions = {
            UserRole.ADMIN: "Administrator with full system access",
            UserRole.ANALYST: "Data analyst with model training and forecasting capabilities",
            UserRole.TRADER: "Trader with view-only access to forecasts and risk metrics",
            UserRole.VIEWER: "Viewer with read-only access to data and reports",
            UserRole.USER: "Standard user with basic access",
        }
        return descriptions.get(role, "Unknown role")
