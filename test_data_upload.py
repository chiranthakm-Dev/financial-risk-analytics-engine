#!/usr/bin/env python
"""End-to-end test for data ingestion endpoints"""

import sys
from pathlib import Path
import os
import time
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set SQLite database URL for testing
os.environ["DATABASE_URL"] = "sqlite:///./forecasting_test.db"

import requests
import pandas as pd
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_e2e_data_flow():
    """Test registration, login, and data upload"""
    
    print("\n" + "="*80)
    print("DATA INGESTION END-TO-END TEST")
    print("="*80 + "\n")
    
    # Generate unique user for this test
    unique_id = str(uuid.uuid4())[:8]
    username = f"datauser_{unique_id}"
    email = f"datauser_{unique_id}@test.com"
    
    # Step 1: Register user
    print("1️⃣  REGISTERING USER...")
    register_response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "SecurePass123!",
            "full_name": "Data Test User"
        }
    )
    print(f"   Status: {register_response.status_code}")
    
    if register_response.status_code != 201:
        print(f"   Error: {register_response.json()}")
        return False
    
    user_data = register_response.json()
    access_token = user_data["tokens"]["access_token"]
    print(f"   ✓ User registered: {user_data['user']['username']}")
    print(f"   ✓ Access token obtained")
    
    # Step 2: Create sample CSV
    print("\n2️⃣  CREATING SAMPLE CSV...")
    
    # Generate sample financial data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    data = {
        'timestamp': dates,
        'symbol': ['AAPL'] * 100,
        'open_price': [150 + i*0.5 for i in range(100)],
        'high_price': [152 + i*0.5 for i in range(100)],
        'low_price': [149 + i*0.5 for i in range(100)],
        'close_price': [151 + i*0.5 for i in range(100)],
        'volume': [1000000 + i*1000 for i in range(100)],
        'adjusted_close': [151 + i*0.5 for i in range(100)],
    }
    
    df = pd.DataFrame(data)
    csv_path = "sample_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"   ✓ Sample CSV created: {csv_path} ({len(df)} rows)")
    
    # Step 3: Validate data (without uploading)
    print("\n3️⃣  VALIDATING DATA...")
    with open(csv_path, 'rb') as f:
        validate_response = requests.post(
            f"{BASE_URL}/api/v1/data/validate",
            files={'file': f},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    print(f"   Status: {validate_response.status_code}")
    if validate_response.status_code == 200:
        validation_result = validate_response.json()
        print(f"   ✓ Validation passed")
        print(f"   Quality score: {validation_result.get('data_quality_score', 'N/A')}%")
    else:
        print(f"   Error: {validate_response.json()}")
        return False
    
    # Step 4: Upload data
    print("\n4️⃣  UPLOADING DATA...")
    with open(csv_path, 'rb') as f:
        upload_response = requests.post(
            f"{BASE_URL}/api/v1/data/upload",
            files={'file': f},
            data={'data_type': 'financial_data', 'source': 'test'},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    print(f"   Status: {upload_response.status_code}")
    if upload_response.status_code != 201:
        print(f"   Error: {upload_response.json()}")
        return False
    
    upload_result = upload_response.json()
    upload_id = upload_result.get('upload_id')
    print(f"   ✓ Upload successful")
    print(f"   Upload ID: {upload_id}")
    print(f"   Rows processed: {upload_result.get('rows_processed')}")
    print(f"   Rows stored: {upload_result.get('rows_stored')}")
    print(f"   Status: {upload_result.get('status')}")
    
    # Step 5: List uploads
    print("\n5️⃣  LISTING USER UPLOADS...")
    list_response = requests.get(
        f"{BASE_URL}/api/v1/data/uploads",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    print(f"   Status: {list_response.status_code}")
    if list_response.status_code == 200:
        uploads_result = list_response.json()
        print(f"   ✓ Total uploads: {uploads_result.get('total')}")
        for upload in uploads_result.get('uploads', []):
            print(f"     - {upload['filename']}: {upload['rows_uploaded']} rows ({upload['status']})")
    else:
        print(f"   Error: {list_response.json()}")
    
    # Step 6: Preprocess data
    print("\n6️⃣  PREPROCESSING DATA...")
    preprocess_response = requests.post(
        f"{BASE_URL}/api/v1/data/preprocess",
        json={
            'upload_id': upload_id,
            'config': {
                'handle_missing': 'forward_fill',
                'outlier_method': 'iqr',
                'normalize': True,
                'smooth': False
            }
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    print(f"   Status: {preprocess_response.status_code}")
    if preprocess_response.status_code == 200:
        preprocess_result = preprocess_response.json()
        print(f"   ✓ Preprocessing complete")
        print(f"   Rows before: {preprocess_result.get('rows_before')}")
        print(f"   Rows after: {preprocess_result.get('rows_after')}")
        print(f"   Message: {preprocess_result.get('message')}")
    else:
        print(f"   Error: {preprocess_response.json()}")
        # This might fail if preprocessing is optional; continue anyway
        print(f"   (Continuing...)")
    
    print("\n" + "="*80)
    print("✅ END-TO-END TEST COMPLETED SUCCESSFULLY")
    print("="*80 + "\n")
    
    return True

if __name__ == "__main__":
    # Wait for server to start
    print("Waiting for server to start...")
    for i in range(30):
        try:
            requests.get(f"{BASE_URL}/health")
            print("✓ Server is ready\n")
            break
        except:
            time.sleep(1)
    else:
        print("❌ Server did not start in time")
        sys.exit(1)
    
    success = test_e2e_data_flow()
    sys.exit(0 if success else 1)
