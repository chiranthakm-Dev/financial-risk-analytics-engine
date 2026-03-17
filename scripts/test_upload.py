#!/usr/bin/env python3
"""Test script: register/login and upload CSV to data ingestion endpoint"""
import requests
import time
import os

BASE = os.environ.get('API_BASE', 'http://127.0.0.1:8000')
REGISTER_URL = f"{BASE}/api/v1/auth/register"
LOGIN_URL = f"{BASE}/api/v1/auth/login"
UPLOAD_URL = f"{BASE}/api/v1/data/upload"

USER = {
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "Password1",
    "full_name": "Test User"
}

session = requests.Session()

# Try to register (ignore conflict)
print('Registering user...')
resp = session.post(REGISTER_URL, json=USER)
print('Register response:', resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)

# Login
print('Logging in...')
resp = session.post(LOGIN_URL, json={"username": USER['username'], "password": USER['password']})
print('Login response:', resp.status_code)
print(resp.text)
if resp.status_code != 200:
    raise SystemExit('Login failed')

data = resp.json()
access = data.get('tokens', {}).get('access_token') or data.get('access_token')
if not access:
    raise SystemExit('No access token received')

headers = { 'Authorization': f'Bearer {access}' }

# Upload file
print('Uploading CSV...')
files = { 'file': open('sample_data.csv', 'rb') }
params = { 'data_type': 'time_series' }
resp = session.post(UPLOAD_URL, headers=headers, files=files, data=params)
print('Upload response:', resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)
