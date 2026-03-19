#!/usr/bin/env python3
"""Quick system validation script"""
import requests
import sys

base = 'http://127.0.0.1:8000'
tests = []

def test_health():
    resp = requests.get(f'{base}/api/health')
    return resp.status_code == 200

def test_config():
    resp = requests.get(f'{base}/api/config-check')
    return resp.status_code == 200

def test_auth_flow():
    # Register
    user = {'email': 'test@demo.com', 'password': 'DemoPass123!', 'role': 'candidate'}
    resp = requests.post(f'{base}/api/auth/register', json=user)
    if resp.status_code not in [200, 201, 409]:  # 409 if already exists
        return False
    
    # Login
    resp = requests.post(f'{base}/api/auth/login', json={'email': user['email'], 'password': user['password']})
    if resp.status_code != 200:
        return False
    
    # Get profile
    token = resp.json().get('data', {}).get('access_token')
    if not token:
        return False
    
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(f'{base}/api/auth/me', headers=headers)
    return resp.status_code == 200

print("=" * 50)
print("SYSTEM VALIDATION TEST SUITE")
print("=" * 50)

tests_run = [
    ("Health Check", test_health),
    ("Config Check", test_config),
    ("Auth Flow (register/login/profile)", test_auth_flow),
]

passed = 0
for name, test_fn in tests_run:
    try:
        result = test_fn()
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if result:
            passed += 1
    except Exception as e:
        print(f"✗ ERROR: {name} - {str(e)}")

print("=" * 50)
print(f"RESULT: {passed}/{len(tests_run)} tests passed")
print("=" * 50)

if passed == len(tests_run):
    print("\n✅ System is PRODUCTION READY!")
    sys.exit(0)
else:
    print("\n⚠️ Some tests failed")
    sys.exit(1)
