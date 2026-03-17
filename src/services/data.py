"""Data validation and preprocessing service"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
from loguru import logger
from datetime import datetime, timezone
from sklearn.ensemble import IsolationForest

from src.schemas_data import TimeSeriesDataSchema, PreprocessingConfig


class DataValidator:
    """Validates and cleans incoming data"""
    
    @staticmethod
    def validate_timeseries_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validate time-series data against schema
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Tuple of (valid_df, validation_report)
        """
        valid_rows = []
        invalid_rows = []
        errors = []
        
        logger.info(f"Validating {len(df)} rows of time-series data")
        
        for idx, row in df.iterrows():
            try:
                # Convert row to dict for Pydantic validation
                row_dict = row.to_dict()
                
                # Handle NaN values
                for key, val in row_dict.items():
                    if pd.isna(val):
                        row_dict[key] = None
                
                # Validate using schema
                TimeSeriesDataSchema(**row_dict)
                valid_rows.append(idx)
            except Exception as e:
                invalid_rows.append(idx)
                errors.append({
                    "row": idx,
                    "error": str(e),
                    "data": row.to_dict()
                })
        
        # Create valid dataframe
        valid_df = df.loc[valid_rows].copy()
        
        # Calculate quality score
        total_rows = len(df)
        valid_count = len(valid_rows)
        data_quality_score = (valid_count / total_rows * 100) if total_rows > 0 else 0
        
        report = {
            "valid_rows": valid_count,
            "invalid_rows": len(invalid_rows),
            "total_rows": total_rows,
            "errors": errors[:10],  # First 10 errors
            "warnings": [],
            "data_quality_score": round(data_quality_score, 2)
        }
        
        logger.info(f"Validation complete: {valid_count}/{total_rows} valid rows ({data_quality_score:.1f}%)")
        
        return valid_df, report
    
    @staticmethod
    def check_missing_values(df: pd.DataFrame) -> Dict[str, int]:
        """
        Check for missing values in each column
        
        Args:
            df: DataFrame to check
            
        Returns:
            Dictionary with missing value counts per column
        """
        missing = df.isnull().sum()
        return missing[missing > 0].to_dict()
    
    @staticmethod
    def check_duplicates(df: pd.DataFrame, subset: List[str] = None) -> int:
        """
        Check for duplicate rows
        
        Args:
            df: DataFrame to check
            subset: Columns to check for duplicates
            
        Returns:
            Number of duplicate rows
        """
        if subset:
            duplicates = df.duplicated(subset=subset).sum()
        else:
            duplicates = df.duplicated().sum()
        return duplicates


class DataPreprocessor:
    """Preprocesses and cleans data"""
    
    @staticmethod
    def handle_missing_values(df: pd.DataFrame, method: str = "forward_fill") -> pd.DataFrame:
        """
        Handle missing values in data
        
        Args:
            df: DataFrame with potential missing values
            method: Strategy (forward_fill, interpolate, drop, bfill)
            
        Returns:
            DataFrame with missing values handled
        """
        df_processed = df.copy()
        rows_before = len(df_processed)
        
        if method == "forward_fill":
            df_processed = df_processed.fillna(method='ffill').fillna(method='bfill')
            handled = df_processed.isnull().sum().sum()
            logger.info(f"Forward-filled {handled} missing values")
        
        elif method == "interpolate":
            # Interpolate numeric columns
            numeric_cols = df_processed.select_dtypes(include=[np.number]).columns
            df_processed[numeric_cols] = df_processed[numeric_cols].interpolate(method='linear', limit_direction='both')
            df_processed = df_processed.fillna(method='bfill').fillna(method='ffill')
            logger.info(f"Interpolated missing values")
        
        elif method == "drop":
            df_processed = df_processed.dropna()
            rows_after = len(df_processed)
            logger.info(f"Dropped {rows_before - rows_after} rows with missing values")
        
        elif method == "bfill":
            df_processed = df_processed.fillna(method='bfill').fillna(method='ffill')
            logger.info(f"Backward-filled missing values")
        
        return df_processed
    
    @staticmethod
    def remove_outliers(df: pd.DataFrame, method: str = "iqr", threshold: float = 1.5, 
                        columns: List[str] = None) -> Tuple[pd.DataFrame, int]:
        """
        Remove outliers from data
        
        Args:
            df: DataFrame to process
            method: Detection method (iqr, zscore, isolation_forest)
            threshold: Threshold for detection
            columns: Specific columns to check
            
        Returns:
            Tuple of (cleaned_df, outliers_removed)
        """
        df_processed = df.copy()
        rows_before = len(df_processed)
        
        if columns is None:
            columns = df_processed.select_dtypes(include=[np.number]).columns.tolist()
        
        if method == "iqr":
            for col in columns:
                Q1 = df_processed[col].quantile(0.25)
                Q3 = df_processed[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                df_processed = df_processed[(df_processed[col] >= lower_bound) & (df_processed[col] <= upper_bound)]
        
        elif method == "zscore":
            from scipy import stats
            z_scores = np.abs(stats.zscore(df_processed[columns].fillna(0)))
            df_processed = df_processed[(z_scores < threshold).all(axis=1)]
        
        elif method == "isolation_forest":
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            outlier_mask = iso_forest.fit_predict(df_processed[columns].fillna(0))
            df_processed = df_processed[outlier_mask != -1]
        
        outliers_removed = rows_before - len(df_processed)
        logger.info(f"Removed {outliers_removed} outliers using {method} method")
        
        return df_processed, outliers_removed
    
    @staticmethod
    def normalize_prices(df: pd.DataFrame, price_columns: List[str] = None) -> pd.DataFrame:
        """
        Normalize price columns to 0-1 range
        
        Args:
            df: DataFrame to process
            price_columns: Columns to normalize
            
        Returns:
            DataFrame with normalized prices
        """
        df_processed = df.copy()
        
        if price_columns is None:
            price_columns = ['open_price', 'high_price', 'low_price', 'close_price', 'adjusted_close']
            price_columns = [col for col in price_columns if col in df_processed.columns]
        
        for col in price_columns:
            if col in df_processed.columns:
                min_val = df_processed[col].min()
                max_val = df_processed[col].max()
                if max_val > min_val:
                    df_processed[col] = (df_processed[col] - min_val) / (max_val - min_val)
        
        logger.info(f"Normalized {len(price_columns)} price columns")
        return df_processed
    
    @staticmethod
    def smooth_data(df: pd.DataFrame, window: int = 5, columns: List[str] = None) -> pd.DataFrame:
        """
        Apply rolling average smoothing
        
        Args:
            df: DataFrame to process
            window: Rolling window size
            columns: Columns to smooth
            
        Returns:
            Smoothed DataFrame
        """
        df_processed = df.copy()
        
        if columns is None:
            columns = df_processed.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].rolling(window=window, center=True).mean()
        
        # Fill NaN values created by rolling
        df_processed = df_processed.fillna(method='bfill').fillna(method='ffill')
        
        logger.info(f"Applied rolling average smoothing (window={window})")
        return df_processed
    
    @staticmethod
    def preprocess(df: pd.DataFrame, config: PreprocessingConfig) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply complete preprocessing pipeline
        
        Args:
            df: Input DataFrame
            config: Preprocessing configuration
            
        Returns:
            Tuple of (processed_df, report)
        """
        logger.info("Starting data preprocessing pipeline")
        df_processed = df.copy()
        rows_before = len(df_processed)
        report = {
            "rows_before": rows_before,
            "rows_after": 0,
            "outliers_removed": 0,
            "missing_handled": 0
        }
        
        # Handle missing values
        if config.handle_missing != "none":
            missing_count = df_processed.isnull().sum().sum()
            if missing_count > 0:
                df_processed = DataPreprocessor.handle_missing_values(df_processed, config.handle_missing)
                report["missing_handled"] = missing_count
        
        # Remove outliers
        if config.remove_outliers:
            price_cols = [col for col in ['open_price', 'high_price', 'low_price', 'close_price'] 
                         if col in df_processed.columns]
            df_processed, outliers = DataPreprocessor.remove_outliers(
                df_processed, 
                method=config.outlier_method,
                threshold=config.outlier_threshold,
                columns=price_cols
            )
            report["outliers_removed"] = outliers
        
        # Normalize prices
        if config.normalize_prices:
            df_processed = DataPreprocessor.normalize_prices(df_processed)
        
        # Smooth data
        if config.smooth_data:
            df_processed = DataPreprocessor.smooth_data(df_processed, window=config.smooth_window)
        
        rows_after = len(df_processed)
        report["rows_after"] = rows_after
        
        logger.info(f"Preprocessing complete: {rows_before} → {rows_after} rows")
        
        return df_processed, report
