"""SQLAlchemy database models for the application"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, 
    Boolean, Text, ForeignKey, Index, JSON, 
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from enum import Enum
import uuid

from src.database import Base


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class ModelType(str, Enum):
    """Model type enumeration"""
    LINEAR_REGRESSION = "linear_regression"
    RIDGE_REGRESSION = "ridge_regression"
    LASSO_REGRESSION = "lasso_regression"
    ARIMA = "arima"
    SARIMA = "sarima"


class ForecastType(str, Enum):
    """Forecast type enumeration"""
    REVENUE = "revenue"
    EXPENSE = "expense"
    CASH_FLOW = "cash_flow"


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    data_uploads = relationship("DataUpload", back_populates="user", cascade="all, delete-orphan")
    trained_models = relationship("TrainedModel", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_username", "username"),
    )


class DataUpload(Base):
    """Data upload records"""
    __tablename__ = "data_uploads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)  # e.g., "financial_data", "time_series"
    row_count = Column(Integer, nullable=False)
    status = Column(String(50), default="validated", nullable=False)  # validated, processing, error
    error_message = Column(Text)
    schema_info = Column(JSON)  # Store schema info, column names, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="data_uploads")
    timeseries_data = relationship("TimeSeriesData", back_populates="data_upload", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_upload_user_id", "user_id"),
        Index("idx_upload_created_at", "created_at"),
    )


class TimeSeriesData(Base):
    """Time-series financial data storage"""
    __tablename__ = "timeseries_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data_upload_id = Column(String(36), ForeignKey("data_uploads.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)  # e.g., "revenue", "expense", "cash_flow"
    attributes = Column(JSON)  # Additional attributes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    data_upload = relationship("DataUpload", back_populates="timeseries_data")

    __table_args__ = (
        Index("idx_ts_upload_id", "data_upload_id"),
        Index("idx_ts_timestamp", "timestamp"),
        Index("idx_ts_category_timestamp", "category", "timestamp"),
    )


class TrainedModel(Base):
    """Trained ML model metadata and versioning"""
    __tablename__ = "trained_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_type = Column(SQLEnum(ModelType), nullable=False)
    forecast_type = Column(SQLEnum(ForecastType), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    model_path = Column(String(255), nullable=False)  # Path to saved model file
    
    # Model performance metrics
    mae = Column(Float)  # Mean Absolute Error
    rmse = Column(Float)  # Root Mean Squared Error
    r2_score = Column(Float)  # R² score
    mape = Column(Float)  # Mean Absolute Percentage Error
    
    # Configuration
    training_data_count = Column(Integer)
    model_params = Column(JSON)  # Store model hyperparameters
    
    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="trained_models")
    forecasts = relationship("Forecast", back_populates="model", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_model_user_id", "user_id"),
        Index("idx_model_name", "model_name"),
        Index("idx_model_active", "is_active"),
    )


class Forecast(Base):
    """Generated forecasts"""
    __tablename__ = "forecasts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(36), ForeignKey("trained_models.id", ondelete="CASCADE"), nullable=False)
    forecast_date = Column(DateTime, nullable=False)
    predicted_value = Column(Float, nullable=False)
    lower_confidence_interval = Column(Float)  # 95% CI lower bound
    upper_confidence_interval = Column(Float)  # 95% CI upper bound
    actual_value = Column(Float)  # Filled in later for backtesting
    forecast_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    model = relationship("TrainedModel", back_populates="forecasts")

    __table_args__ = (
        Index("idx_forecast_model_id", "model_id"),
        Index("idx_forecast_date", "forecast_date"),
    )


class RiskMetrics(Base):
    """Computed risk metrics and analytics"""
    __tablename__ = "risk_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(36), ForeignKey("trained_models.id", ondelete="CASCADE"), nullable=False)
    calculation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Risk metrics
    volatility = Column(Float)  # Standard deviation
    var_95 = Column(Float)  # Value at Risk at 95% confidence
    var_99 = Column(Float)  # Value at Risk at 99% confidence
    cvar_95 = Column(Float)  # Conditional VaR at 95% confidence
    cvar_99 = Column(Float)  # Conditional VaR at 99% confidence
    sharpe_ratio = Column(Float)  # Risk-adjusted return metric
    
    # Additional analytics
    correlation_data = Column(JSON)  # Store correlations with other variables
    scenario_data = Column(JSON)  # Monte Carlo simulation results
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_risk_model_id", "model_id"),
        Index("idx_risk_calculation_date", "calculation_date"),
    )


class KPIReport(Base):
    """Generated KPI reports"""
    __tablename__ = "kpi_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(36), ForeignKey("trained_models.id", ondelete="CASCADE"), nullable=False)
    report_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    report_period_start = Column(DateTime, nullable=False)
    report_period_end = Column(DateTime, nullable=False)
    
    # KPI metrics
    revenue_growth_rate = Column(Float)
    operating_margin = Column(Float)
    net_margin = Column(Float)
    forecast_accuracy = Column(Float)
    budget_variance = Column(Float)
    risk_adjusted_return = Column(Float)
    
    # Report data
    report_data = Column(JSON)  # Full report data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_kpi_model_id", "model_id"),
        Index("idx_kpi_report_date", "report_date"),
    )
