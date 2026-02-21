"""Main FastAPI application entry point"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from jose import JWTError

from config.settings import get_settings
from src.routes import auth

# Configure logger
settings = get_settings()
logger.remove()
logger.add(
    sys.stderr,
    format=settings.log_format,
    level=settings.log_level
)
logger.add(
    "logs/app.log",
    format=settings.log_format,
    level=settings.log_level,
    rotation="500 MB"
)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API-driven analytics platform for financial forecasting and risk assessment",
    debug=settings.debug,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints"
        },
        {
            "name": "Health",
            "description": "System health and status endpoints"
        },
        {
            "name": "Root",
            "description": "Root endpoint"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        },
    )

@app.exception_handler(JWTError)
async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT exceptions"""
    logger.warning(f"JWT exception: {str(exc)}")
    return JSONResponse(
        status_code=401,
        content={
            "error": "Invalid or expired token",
            "status_code": 401,
            "path": str(request.url.path)
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected exception: {str(exc)}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": str(request.url.path)
        },
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "api_endpoints": {
            "health": "/health",
            "authentication": "/api/v1/auth"
        }
    }

# Include routers
app.include_router(auth.router)

# Import other routers (will be created in later tasks)
# from src.routes import data_ingestion, forecasting, risk_analytics, kpi

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(f"Application started: {settings.app_name} v{settings.app_version}")
    logger.debug(f"Debug mode: {settings.debug}")
    logger.debug(f"Database: {settings.database_url}")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info(f"Application shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug
    )
