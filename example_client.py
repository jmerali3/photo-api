#!/usr/bin/env python3
"""
Example client for photo-api showing how to authenticate and use the API.
"""

import requests
import os

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change to your hosted backend URL
API_KEY = os.getenv("API_KEY", "dev-api-key-replace-me-in-production")  # Use your actual API key

def make_authenticated_request(method, endpoint, **kwargs):
    """Make an authenticated request to the API"""
    headers = kwargs.get('headers', {})
    headers['Authorization'] = f'Bearer {API_KEY}'
    kwargs['headers'] = headers

    url = f"{API_BASE_URL}{endpoint}"
    response = requests.request(method, url, **kwargs)
    return response

def test_health():
    """Test the health endpoint (no auth required)"""
    print("Testing health endpoint...")
    response = requests.get(f"{API_BASE_URL}/healthz")
    print(f"Health check: {response.status_code} - {response.json()}")

def test_init_upload():
    """Test initializing an upload (requires auth)"""
    print("\nTesting upload initialization...")

    payload = {
        "content_type": "image/jpeg",
        "max_bytes": 5000000,
        "key_prefix": "test-uploads"
    }

    response = make_authenticated_request("POST", "/uploads/init", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"Upload init successful!")
        print(f"Upload URL: {data['url']}")
        print(f"S3 Key: {data['key']}")
        return data
    else:
        print(f"Upload init failed: {response.status_code} - {response.text}")
        return None

def test_job_status():
    """Test job status endpoint (requires auth)"""
    print("\nTesting job status...")

    # This will fail because the job doesn't exist, but it tests auth
    response = make_authenticated_request("GET", "/jobs/test-job-id")
    print(f"Job status: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("Photo API Client Example")
    print("=" * 40)

    # Test endpoints
    test_health()
    test_init_upload()
    test_job_status()

    print("\nDone! If you see 401 errors, check your API key.")
    print("If you see CORS errors, make sure your local client URL is in CORS_ORIGINS.")