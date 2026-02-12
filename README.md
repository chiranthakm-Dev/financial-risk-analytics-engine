# Financial Forecasting & Risk Analytics Engine

A Python-based, API-driven analytics platform designed to provide forward-looking financial projections, quantitative risk assessment, and automated KPI reporting.

## Overview

This system replaces spreadsheet-driven forecasting with governed, model-backed financial planning. Built using FastAPI, PostgreSQL, and open-source ML libraries for a zero-cost, scalable, and production-ready architecture suitable for financial environments.

## Features

- **Financial Forecasting**: Revenue, expense, and cash flow predictions using regression and time-series models
- **Risk Analytics**: Volatility, VaR, CVaR, Sharpe Ratio, and Monte Carlo simulations
- **KPI Reporting**: Automated generation of key performance indicators and metrics
- **REST API**: Fully documented API endpoints with Swagger UI
- **Authentication**: JWT-based authentication with RBAC
- **Containerized**: Docker support for easy deployment

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- Uvicorn

### Data Processing & ML
- Pandas, NumPy
- Scikit-learn, Statsmodels, SciPy
- Joblib (Model persistence)

### Database
- PostgreSQL
- SQLAlchemy ORM
- Alembic (Migrations)

### DevOps
- Docker
- Docker Compose

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- pip and virtualenv

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/chiranthakm-Dev/financial-risk-analytics-engine.git
   cd financial-risk-analytics-engine
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   alembic upgrade head
   ```

6. **Run the application**
   ```bash
   python src/main.py
   # or use the startup script
   ./run.sh
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
.
├── src/                    # Source code
│   ├── main.py            # FastAPI application entry point
│   ├── routes/            # API route handlers (TBD)
│   ├── models/            # Database models (TBD)
│   ├── services/          # Business logic (TBD)
│   └── utils/             # Utility functions (TBD)
├── config/                # Configuration files
│   └── settings.py        # Application settings
├── tests/                 # Test suite
├── models/                # Saved ML models
├── logs/                  # Application logs
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
├── pytest.ini            # Pytest configuration
├── pyproject.toml        # Project metadata
├── .env                  # Environment variables (local)
└── README.md             # This file
```

## Development

### Running tests
```bash
pytest
pytest --cov=src  # With coverage
```

### Code formatting
```bash
black src tests
isort src tests
```

### Type checking
```bash
mypy src
```

### Linting
```bash
flake8 src tests
```

## Configuration

All configuration is managed via environment variables in `.env` file:

```env
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=False

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/forecasting_db

# JWT
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Cache (Optional)
ENABLE_CACHE=False
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

## Deployment

### Docker

1. **Build image**
   ```bash
   docker build -t forecasting-engine .
   ```

2. **Run container**
   ```bash
   docker run -p 8000:8000 --env-file .env forecasting-engine
   ```

3. **Using Docker Compose** (TBD)
   ```bash
   docker-compose up -d
   ```

## API Endpoints (Coming Soon)

- `POST /upload-data` - Upload financial data
- `POST /train-model` - Train forecasting model
- `GET /forecast` - Generate forecasts
- `GET /risk-metrics` - Calculate risk metrics
- `POST /run-simulation` - Run Monte Carlo simulation
- `GET /kpi-report` - Generate KPI report

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and formatting
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please create an issue on GitHub.

---

**Status**: In Development (Phase 1)  
**Last Updated**: February 2026
