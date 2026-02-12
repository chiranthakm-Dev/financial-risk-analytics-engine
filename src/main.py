"""Main FastAPI application entry point"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import get_settings

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
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "docs": "/docs"
    }

# Import and include routers (will be created in later tasks)
# from src.routes import auth, data_ingestion, forecasting, risk_analytics, kpi

logger.info(f"Application initialized: {settings.app_name} v{settings.app_version}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug
    )
