# Database Layer Documentation

## Overview

The database layer uses PostgreSQL with SQLAlchemy ORM and Alembic for schema migrations. The system is designed for financial data management with comprehensive tracking of users, forecasts, risk metrics, and KPI reports.

## Database Models

### 1. User
- **Table**: `users`
- **Purpose**: User authentication and authorization
- **Key Fields**:
  - `id`: UUID primary key
  - `username`: Unique username
  - `email`: Unique email address
  - `hashed_password`: Bcrypt hashed password
  - `role`: User role (admin, analyst, viewer)
  - `is_active`: Account status
  - `created_at`, `updated_at`: Timestamps

**Relationships**: 
- One User → Many DataUploads
- One User → Many TrainedModels

### 2. DataUpload
- **Table**: `data_uploads`
- **Purpose**: Track uploaded financial data files
- **Key Fields**:
  - `id`: UUID primary key
  - `user_id`: Foreign key to User
  - `filename`: Uploaded file name
  - `data_type`: Type of data (financial_data, time_series, etc.)
  - `row_count`: Number of rows in dataset
  - `status`: Processing status (validated, processing, error)
  - `metadata`: JSON metadata (schema, columns, etc.)
  - `created_at`, `updated_at`: Timestamps

**Relationships**:
- Many TimeSeriesData → One DataUpload

### 3. TimeSeriesData
- **Table**: `timeseries_data`
- **Purpose**: Store individual time-series data points
- **Key Fields**:
  - `id`: UUID primary key
  - `data_upload_id`: Foreign key to DataUpload
  - `timestamp`: Date/time of data point
  - `value`: Numeric value
  - `category`: Data category (revenue, expense, cash_flow)
  - `metadata`: Additional JSON attributes
  - `created_at`: Creation timestamp

**Indexes**:
- `(timestamp)`
- `(data_upload_id, timestamp)`
- `(category, timestamp)`

### 4. TrainedModel
- **Table**: `trained_models`
- **Purpose**: Store ML model metadata and versioning
- **Key Fields**:
  - `id`: UUID primary key
  - `user_id`: Foreign key to User
  - `model_name`: Descriptive model name
  - `model_type`: Type (linear_regression, arima, sarima, etc.)
  - `forecast_type`: Forecast category (revenue, expense, cash_flow)
  - `version`: Model version number
  - `model_path`: Path to serialized model file
  - `mae`, `rmse`, `r2_score`, `mape`: Performance metrics
  - `hyperparameters`: JSON hyperparameter configuration
  - `is_active`: Active status for production
  - `created_at`, `updated_at`: Timestamps

**Relationships**:
- Many Forecasts → One TrainedModel
- Many RiskMetrics → One TrainedModel
- Many KPIReports → One TrainedModel

### 5. Forecast
- **Table**: `forecasts`
- **Purpose**: Store generated forecast predictions
- **Key Fields**:
  - `id`: UUID primary key
  - `model_id`: Foreign key to TrainedModel
  - `forecast_date`: Date of prediction
  - `predicted_value`: Forecasted value
  - `lower_confidence_interval`: 95% CI lower bound
  - `upper_confidence_interval`: 95% CI upper bound
  - `actual_value`: Actual value (for backtesting)
  - `metadata`: Additional JSON data
  - `created_at`: Timestamp

**Indexes**:
- `(model_id)`
- `(forecast_date)`

### 6. RiskMetrics
- **Table**: `risk_metrics`
- **Purpose**: Store computed risk analytics
- **Key Fields**:
  - `id`: UUID primary key
  - `model_id`: Foreign key to TrainedModel
  - `volatility`: Standard deviation
  - `var_95`: Value at Risk at 95% confidence
  - `var_99`: Value at Risk at 99% confidence
  - `cvar_95`: Conditional VaR at 95% confidence
  - `cvar_99`: Conditional VaR at 99% confidence
  - `sharpe_ratio`: Risk-adjusted return metric
  - `correlation_matrix`: JSON correlation data
  - `scenario_results`: JSON Monte Carlo results
  - `calculation_date`: When metrics were computed
  - `created_at`, `updated_at`: Timestamps

**Indexes**:
- `(model_id)`
- `(calculation_date)`

### 7. KPIReport
- **Table**: `kpi_reports`
- **Purpose**: Store generated KPI reports
- **Key Fields**:
  - `id`: UUID primary key
  - `model_id`: Foreign key to TrainedModel
  - `report_date`: When report was generated
  - `report_period_start`: Period start date
  - `report_period_end`: Period end date
  - `revenue_growth_rate`: KPI value
  - `operating_margin`: KPI value
  - `net_margin`: KPI value
  - `forecast_accuracy`: KPI value
  - `budget_variance`: KPI value
  - `risk_adjusted_return`: KPI value
  - `report_data`: Full JSON report
  - `created_at`: Timestamp

**Indexes**:
- `(model_id)`
- `(report_date)`

## Setup & Migrations

### Initial Setup

1. **Update .env file**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

2. **Initialize database**:
   ```bash
   source venv/bin/activate
   python src/db_init.py setup
   ```

3. **Check database connection**:
   ```bash
   python src/db_init.py check
   ```

4. **Create admin user**:
   ```bash
   python src/db_init.py create-admin
   ```

### Alembic Migrations

**Create a new migration**:
```bash
alembic revision --autogenerate -m "description of changes"
```

**Apply migrations**:
```bash
alembic upgrade head
```

**Rollback migrations**:
```bash
alembic downgrade -1
```

**View migration history**:
```bash
alembic history
```

## Database Configuration

### PostgreSQL (Production)
```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### SQLite (Development)
```
DATABASE_URL=sqlite:///./forecasting.db
```

## Connection Management

The `SessionLocal` factory creates new database sessions:

```python
from src.database import SessionLocal

db = SessionLocal()
try:
    # Use db session
    user = db.query(User).filter(User.id == user_id).first()
finally:
    db.close()
```

FastAPI dependency injection:

```python
from fastapi import Depends
from src.database import get_db

@app.get("/endpoint")
def my_endpoint(db: Session = Depends(get_db)):
    # Use db session
    users = db.query(User).all()
    return users
```

## Query Examples

### Get user with related data uploads
```python
user = db.query(User).filter(User.username == "admin").first()
uploads = user.data_uploads  # Access related data
```

### Get latest forecasts for a model
```python
forecasts = db.query(Forecast)\
    .filter(Forecast.model_id == model_id)\
    .order_by(Forecast.forecast_date.desc())\
    .limit(10)\
    .all()
```

### Get risk metrics for a date range
```python
metrics = db.query(RiskMetrics)\
    .filter(
        RiskMetrics.model_id == model_id,
        RiskMetrics.calculation_date >= start_date,
        RiskMetrics.calculation_date <= end_date
    )\
    .all()
```

## Performance Optimization

### Indexes
All critical fields have indexes for query performance:
- Foreign keys (user_id, model_id, data_upload_id)
- Timestamps (created_at, forecast_date, calculation_date)
- Composite indexes for common filter combinations

### Query Optimization
- Use `.only()` to select specific columns
- Use `.join()` for efficient relationship loading
- Use lazy loading judiciously
- Consider pagination for large result sets

## Troubleshooting

### Connection Errors
```bash
# Test PostgreSQL connection
psql postgresql://user:password@localhost:5432/dbname

# Check Python connection
python src/db_init.py check
```

### Migration Issues
```bash
# View migration status
alembic history

# Reset migrations (development only)
python src/db_init.py reset
```

### Data Issues
```bash
# Create tables manually
python src/db_init.py setup

# Reset all data
python src/db_init.py reset
```

## Best Practices

1. **Always use sessions correctly** - Use try/finally or context managers
2. **Use foreign keys** - Enforce referential integrity
3. **Index strategically** - Index commonly queried fields
4. **Use migrations** - Track all schema changes
5. **Test queries** - Use test database for development
6. **Validate data** - Use Pydantic models for validation
7. **Log operations** - Track important database operations

---

Last Updated: February 2026
