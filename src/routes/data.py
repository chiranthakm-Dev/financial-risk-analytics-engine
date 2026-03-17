"""Data ingestion API routes"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
import pandas as pd
import io
import uuid
from datetime import datetime, timezone
from loguru import logger

from src.database import get_db
from src.models import DataUpload, TimeSeriesData
from src.schemas_data import (
    DataUploadResponse, DataValidationResponse, PreprocessingConfig,
    PreprocessingResponse, DataUploadRequest
)
from src.services.data import DataValidator, DataPreprocessor
from src.middleware.rbac import get_current_user_id, Permission, require_permission

router = APIRouter(
    prefix="/api/v1/data",
    tags=["Data Ingestion"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Server error"},
    },
)


@router.post(
    "/upload",
    response_model=DataUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload financial data",
    description="Upload CSV file containing financial or time-series data"
)
async def upload_data(
    file: UploadFile = File(..., description="CSV file to upload"),
    data_type: str = "time_series",
    source: str = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Upload and process financial data from CSV
    
    - **file**: CSV file with financial data
    - **data_type**: Type of data (time_series, financial_data, market_data)
    - **source**: Optional data source identifier
    
    Supports: OHLCV data, timestamps, symbols
    
    Returns: Upload summary with row counts and status
    """
    upload_id = str(uuid.uuid4())
    
    try:
        # Read file
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        logger.info(f"File uploaded: {file.filename} ({len(df)} rows)")
        
        # Validate data
        valid_df, validation_report = DataValidator.validate_timeseries_data(df)
        
        if validation_report["data_quality_score"] < 50:
            logger.warning(f"Low data quality: {validation_report['data_quality_score']}%")
        
        # Create upload record
        upload_record = DataUpload(
            id=upload_id,
            user_id=user_id,
            filename=file.filename,
            data_type=data_type,
            rows_uploaded=len(df),
            rows_valid=len(valid_df),
            status="completed" if len(valid_df) > 0 else "failed",
            source=source,
            upload_metadata={
                "original_columns": df.columns.tolist(),
                "data_quality": validation_report["data_quality_score"]
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(upload_record)
        
        # Store valid data
        stored_count = 0
        if len(valid_df) > 0:
            for idx, row in valid_df.iterrows():
                try:
                    ts_data = TimeSeriesData(
                        id=str(uuid.uuid4()),
                        upload_id=upload_id,
                        user_id=user_id,
                        timestamp=pd.to_datetime(row['timestamp']),
                        symbol=str(row['symbol']),
                        open_price=float(row['open_price']),
                        high_price=float(row['high_price']),
                        low_price=float(row['low_price']),
                        close_price=float(row['close_price']),
                        volume=int(row['volume']),
                        adjusted_close=float(row.get('adjusted_close')) if pd.notna(row.get('adjusted_close')) else None,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(ts_data)
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing row {idx}: {str(e)}")
                    continue
        
        db.commit()
        
        logger.info(f"Upload {upload_id}: {stored_count} rows stored")
        
        return {
            "upload_id": upload_id,
            "filename": file.filename,
            "rows_processed": len(df),
            "rows_stored": stored_count,
            "data_type": data_type,
            "status": "success" if stored_count == len(valid_df) else "partial",
            "message": f"Successfully stored {stored_count}/{len(df)} rows",
            "created_at": datetime.now(timezone.utc)
        }
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing file: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=DataValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate CSV data",
    description="Validate data without storing"
)
async def validate_data(
    file: UploadFile = File(..., description="CSV file to validate"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Validate CSV data against schema without storing
    
    - **file**: CSV file to validate
    
    Returns: Validation report with quality score and errors
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        logger.info(f"Validating file: {file.filename} ({len(df)} rows)")
        
        valid_df, validation_report = DataValidator.validate_timeseries_data(df)
        
        return validation_report
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error validating file: {str(e)}"
        )


@router.post(
    "/preprocess",
    response_model=PreprocessingResponse,
    status_code=status.HTTP_200_OK,
    summary="Preprocess uploaded data",
    description="Apply preprocessing pipeline to stored data"
)
async def preprocess_data(
    upload_id: str,
    config: PreprocessingConfig = PreprocessingConfig(),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> dict:
    """
    Apply preprocessing to data from an upload
    
    - **upload_id**: ID of the upload to preprocess
    - **config**: Preprocessing configuration
    
    Handles:
    - Missing values (forward_fill, interpolate, drop)
    - Outlier detection (IQR, zscore, isolation_forest)
    - Data normalization
    - Smoothing
    
    Returns: Preprocessing summary with before/after counts
    """
    try:
        # Get uploaded data
        upload = db.query(DataUpload).filter(DataUpload.id == upload_id).first()
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        # Check authorization
        if upload.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to preprocess this data"
            )
        
        # Load data
        ts_data = db.query(TimeSeriesData).filter(
            TimeSeriesData.upload_id == upload_id
        ).all()
        
        if not ts_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for this upload"
            )
        
        # Convert to DataFrame
        data_list = []
        for record in ts_data:
            data_list.append({
                'timestamp': record.timestamp,
                'symbol': record.symbol,
                'open_price': record.open_price,
                'high_price': record.high_price,
                'low_price': record.low_price,
                'close_price': record.close_price,
                'volume': record.volume,
                'adjusted_close': record.adjusted_close,
            })
        
        df = pd.DataFrame(data_list)
        
        logger.info(f"Processing {len(df)} rows with config: {config.dict()}")
        
        # Apply preprocessing
        processed_df, preprocess_report = DataPreprocessor.preprocess(df, config)
        
        # Update upload metadata
        # Update upload metadata (use upload_metadata field)
        upload.upload_metadata = {
            **(upload.upload_metadata or {}),
            "preprocessing": preprocess_report
        }
        upload.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "rows_before": preprocess_report["rows_before"],
            "rows_after": preprocess_report["rows_after"],
            "outliers_removed": preprocess_report["outliers_removed"],
            "missing_handled": preprocess_report["missing_handled"],
            "message": f"Preprocessing complete: {preprocess_report['rows_before']} → {preprocess_report['rows_after']} rows"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preprocessing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error preprocessing data: {str(e)}"
        )


@router.get(
    "/uploads",
    status_code=status.HTTP_200_OK,
    summary="List user's data uploads",
    description="Get list of all uploads by the current user"
)
async def list_uploads(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
) -> dict:
    """
    List all data uploads by the current user
    
    - **limit**: Maximum number of uploads to return
    - **offset**: Number of uploads to skip
    
    Returns: List of upload summaries
    """
    try:
        uploads = db.query(DataUpload).filter(
            DataUpload.user_id == user_id
        ).order_by(DataUpload.created_at.desc()).limit(limit).offset(offset).all()
        
        total = db.query(DataUpload).filter(DataUpload.user_id == user_id).count()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "uploads": [
                {
                    "upload_id": u.id,
                    "filename": u.filename,
                    "data_type": u.data_type,
                    "rows_uploaded": u.rows_uploaded,
                    "rows_valid": u.rows_valid,
                    "status": u.status,
                    "created_at": u.created_at.isoformat(),
                }
                for u in uploads
            ]
        }
    except Exception as e:
        logger.error(f"Error listing uploads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving uploads"
        )
