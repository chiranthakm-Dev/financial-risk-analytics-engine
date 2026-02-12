#!/bin/bash

# Financial Forecasting & Risk Analytics Engine - Development Startup Script

echo "Starting Financial Forecasting & Risk Analytics Engine..."

# Activate virtual environment
source venv/bin/activate

# Set environment to development
export PYTHONUNBUFFERED=1

# Run the FastAPI application with uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
