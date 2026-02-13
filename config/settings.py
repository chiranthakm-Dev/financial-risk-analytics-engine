"""Environment configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Financial Forecasting & Risk Analytics Engine"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server settings
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # Database settings
    database_url: str = "sqlite:///./forecasting.db"  # SQLite for local development
    # For PostgreSQL: database_url: str = "postgresql://user:password@localhost:5432/forecasting_db"
    
    # JWT settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis settings (optional)
    redis_url: str = "redis://localhost:6379/0"
    enable_cache: bool = False
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Model settings
    model_directory: str = "./models"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()
