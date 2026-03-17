"""Pydantic schemas for data ingestion and validation (moved to single module)

This file mirrors the previous `src/schemas/data.py` content but exists as
`src/schemas_data.py` to avoid conflict with the top-level `src/schemas.py` module.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from datetime import datetime


class DataType(str, Enum):
    """Supported data types"""
    FINANCIAL_DATA = "financial_data"
    TIME_SERIES = "time_series"
    MARKET_DATA = "market_data"
    CUSTOM = "custom"


class TimeSeriesDataSchema(BaseModel):
    """Schema for time-series data validation"""
    timestamp: datetime = Field(..., description="Timestamp of the data point")
    symbol: str = Field(..., min_length=1, max_length=20, description="Asset symbol (e.g., AAPL, EURUSD)")
    open_price: float = Field(..., gt=0, description="Opening price")
    high_price: float = Field(..., gt=0, description="High price")
    low_price: float = Field(..., gt=0, description="Low price")
    close_price: float = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    adjusted_close: Optional[float] = Field(None, gt=0, description="Adjusted closing price")
    
    @validator("timestamp", pre=True)
    def parse_timestamp(cls, v):
        """Parse timestamp from string or datetime"""
        if isinstance(v, str):
            # Try multiple formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Invalid timestamp format: {v}")
        return v
    
    @validator("high_price", "low_price", "adjusted_close", pre=True)
    def handle_missing_values(cls, v):
        """Convert empty strings to None"""
        if v == "" or v is None:
            return None
        return v
    
    @validator("close_price", always=True)
    def validate_price_relationships(cls, close_price, values):
        """Validate OHLC price relationships"""
        if 'high_price' in values and 'low_price' in values:
            high = values.get('high_price')
            low = values.get('low_price')
            if high and low:
                if close_price > high or close_price < low:
                    raise ValueError(f"Close price {close_price} outside high-low range [{low}, {high}]")
        return close_price


class FinancialMetricsSchema(BaseModel):
    """Schema for financial metrics data"""
    date: datetime = Field(..., description="Date of the metrics")
    symbol: str = Field(..., description="Asset symbol")
    revenue: float = Field(..., ge=0, description="Revenue")
    operating_income: float = Field(..., description="Operating income")
    net_income: float = Field(..., description="Net income")
    total_assets: float = Field(..., ge=0, description="Total assets")
    total_liabilities: float = Field(..., ge=0, description="Total liabilities")
    equity: float = Field(..., description="Shareholder equity")


class DataValidationResponse(BaseModel):
    """Response for data validation"""
    valid_rows: int = Field(..., description="Number of valid rows")
    invalid_rows: int = Field(..., description="Number of invalid rows")
    total_rows: int = Field(..., description="Total rows processed")
    errors: List[dict] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    data_quality_score: float = Field(..., ge=0, le=100, description="Data quality percentage")


class DataUploadRequest(BaseModel):
    """Request for data upload"""
    data_type: DataType = Field(..., description="Type of data being uploaded")
    source: Optional[str] = Field(None, description="Data source identifier")
    description: Optional[str] = Field(None, description="Description of the data")


class DataUploadResponse(BaseModel):
    """Response after data upload"""
    upload_id: str = Field(..., description="Unique upload ID")
    filename: str = Field(..., description="Original filename")
    rows_processed: int = Field(..., description="Number of rows processed")
    rows_stored: int = Field(..., description="Number of rows successfully stored")
    data_type: str = Field(..., description="Type of data uploaded")
    status: str = Field(..., description="Upload status (success, partial, failed)")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(..., description="Upload timestamp")


class PreprocessingConfig(BaseModel):
    """Configuration for data preprocessing"""
    handle_missing: str = Field("forward_fill", description="Strategy for missing values (forward_fill, interpolate, drop)")
    remove_outliers: bool = Field(True, description="Remove statistical outliers")
    outlier_method: str = Field("iqr", description="Outlier detection method (iqr, zscore, isolation_forest)")
    outlier_threshold: float = Field(3.0, description="Threshold for outlier detection")
    normalize_prices: bool = Field(False, description="Normalize prices to 0-1 range")
    smooth_data: bool = Field(False, description="Apply smoothing (rolling average)")
    smooth_window: int = Field(5, description="Smoothing window size")


class PreprocessingResponse(BaseModel):
    """Response after preprocessing"""
    rows_before: int = Field(..., description="Rows before preprocessing")
    rows_after: int = Field(..., description="Rows after preprocessing")
    outliers_removed: int = Field(..., description="Number of outliers removed")
    missing_handled: int = Field(..., description="Number of missing values handled")
    message: str = Field(..., description="Preprocessing summary")
