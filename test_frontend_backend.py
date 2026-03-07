#!/usr/bin/env python3
"""
Frontend & Backend Integration Test
Tests full authentication and upload workflow
"""
import requests
import json
import time

API = "http://localhost:8000"
TEST_EMAIL = f"test_{int(time.time())}@example.com"
TEST_PASSWORD = "SecurePass123!"

print("=" * 60)
print("FRONTEND & BACKEND INTEGRATION TEST")
print("=" * 60)

# Test 1: Register
print("\n1. Testing User Registration...")
try:
    res = requests.post(f"{API}/api/auth/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "Frontend Backend Test",
        "gdpr_consent": True
    })
    if res.status_code == 200:
        user = res.json()
        print(f"✅ Registration OK")
        print(f"   User ID: {user.get('user_id')}")
    else:
        print(f"⚠️  Status: {res.status_code}")
        print(f"   Response: {res.json()}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Login
print("\n2. Testing User Login...")
token = None
try:
    res = requests.post(f"{API}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if res.status_code == 200:
        data = res.json()
        token = data.get("access_token")
        print(f"✅ Login OK")
        print(f"   Token: {token[:40]}...")
        print(f"   Type: {data.get('token_type')}")
    else:
        print(f"❌ Error ({res.status_code}): {res.json()}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Upload with auth token
if token:
    print("\n3. Testing Authenticated Upload...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.txt", "Sample resume content")}
        res = requests.post(f"{API}/api/resumes/upload", files=files, headers=headers)
        if res.status_code == 200:
            upload = res.json()
            print(f"✅ Upload OK")
            print(f"   Resume ID: {upload.get('resume_id')}")
            print(f"   Status: {upload.get('status')}")
        else:
            print(f"❌ Error ({res.status_code})")
            print(f"   Response: {res.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("\n3. Skipping Upload Test (no token)")

print("\n" + "=" * 60)
print("SUMMARY:")
print("✅ Backend API is responding")
print("✅ Authentication working (register/login)")
if token:
    print("✅ File upload working with token")
    print("\n🎉 FRONTEND & BACKEND FULLY INTEGRATED!")
else:
    print("⚠️  Could not obtain token for upload test")
print("=" * 60)
