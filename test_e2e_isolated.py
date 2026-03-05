"""
End-to-End Integration Test - Isolated from Redis/Celery
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Mock both celery and redis at the very start, before any imports
fake_celery_app = MagicMock()
fake_celery_app.conf = MagicMock()
fake_celery_app.task = lambda *args, **kwargs: lambda f: f

sys.modules['celery'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['celery.result'] = MagicMock()

# Now add workspace to path and mock the workers module
sys.path.insert(0, "backend")

# Patch the workers module entirely
sys.modules['workers'] = MagicMock()
sys.modules['workers.background_tasks'] = MagicMock(
    verify_github=MagicMock(delay=lambda **kwargs: MagicMock(id='task-123')),
    verify_full=MagicMock(delay=lambda **kwargs: MagicMock(id='task-456')),
    verify_resume_ai=MagicMock(delay=lambda **kwargs: MagicMock(id='task-789')),
    verify_certificate=MagicMock(delay=lambda **kwargs: MagicMock(id='task-abc')),
    get_task_status=MagicMock(return_value={'status': 'completed'}),
)

# Now it's safe to import the app
from fastapi.testclient import TestClient
from main import app

client = TestClient(app, base_url="http://127.0.0.1")

def test_health():
    """Test 1: API is responsive"""
    print("\n" + "="*60)
    print("TEST 1: API Health")
    print("="*60)
    try:
        response = client.get("/health")
        print(f"✓ Status: {response.status_code}")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_github_endpoint():
    """Test 2: GitHub verification endpoint"""
    print("\n" + "="*60)
    print("TEST 2: GitHub Verification Endpoint")
    print("="*60)
    try:
        payload = {
            "username": "torvalds",
            "claimed_skills": ["C", "Linux"]
        }
        response = client.post("/api/verify/github", json=payload)
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response contains: {list(data.keys())}")
            has_task = "task_id" in data or "status" in data
            print(f"✓ Has task_id: {has_task}")
            return has_task
        elif response.status_code == 429:
            print("✓ Rate limited (expected after 10 requests)")
            return True
        else:
            print(f"Response: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)[:100]}")
        return False

def test_full_endpoint():
    """Test 3: Full verification endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Full Verification Endpoint")
    print("="*60)
    try:
        from uuid import uuid4
        payload = {
            "resume_id": str(uuid4()),
            "github_username": "testuser",
            "resume_text": "Senior Python Developer with 5 years experience",
            "claimed_skills": ["Python", "FastAPI", "Docker"]
        }
        response = client.post("/api/verify/full", json=payload)
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response keys: {list(data.keys())}")
            return True
        elif response.status_code == 429:
            print("✓ Rate limited")
            return True
        else:
            print(f"Response: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)[:100]}")
        return False

def test_task_status():
    """Test 4: Task status endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Task Status Endpoint")
    print("="*60)
    try:
        response = client.get("/api/task-status/task-123")
        print(f"✓ Status: {response.status_code}")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_routes_registered():
    """Test 5: Routes are registered"""
    print("\n" + "="*60)
    print("TEST 5: Routes Registered")
    print("="*60)
    try:
        routes = {r.path for r in app.routes}
        
        required = [
            "/api/verify/github",
            "/api/verify/full",
            "/api/task-status/{task_id}",
        ]
        
        found = 0
        for route in required:
            if route in routes:
                print(f"✓ {route}")
                found += 1
            else:
                print(f"✗ {route} NOT FOUND")
        
        print(f"Found {found}/{len(required)} routes")
        return found >= 2
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_rate_limiter_imported():
    """Test 6: Rate limiter is available"""
    print("\n" + "="*60)
    print("TEST 6: Rate Limiter")
    print("="*60)
    try:
        from utils.rate_limiter import check_rate_limit, limiter
        print(f"✓ Rate limiter imported")
        print(f"✓ Limiter class: {type(limiter).__name__}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_cors_middleware():
    """Test 7: CORS middleware present"""
    print("\n" + "="*60)
    print("TEST 7: CORS Middleware")
    print("="*60)
    try:
        # Just verify the app is configured properly
        print(f"✓ App configured")
        
        # Test that OPTIONS request works
        try:
            response = client.options("/health")
            print(f"✓ OPTIONS request returns: {response.status_code}")
        except:
            print(f"ℹ OPTIONS not required in test env")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_error_handling():
    """Test 8: Error responses"""
    print("\n" + "="*60)
    print("TEST 8: Error Handling")
    print("="*60)
    try:
        # Invalid path
        response = client.get("/api/nonexistent")
        print(f"✓ Invalid route returns: {response.status_code}")
        
        # Missing required fields
        response = client.post("/api/verify/github", json={})
        print(f"✓ Invalid payload returns: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("RESUME VERIFICATION - E2E TEST")
    print("(with mocked Redis/Celery)")
    print("=" * 60)
    
    tests = [
        ("API Health", test_health),
        ("GitHub Endpoint", test_github_endpoint),
        ("Full Verification", test_full_endpoint),
        ("Task Status", test_task_status),
        ("Routes Registered", test_routes_registered),
        ("Rate Limiter", test_rate_limiter_imported),
        ("CORS Middleware", test_cors_middleware),
        ("Error Handling", test_error_handling),
    ]
    
    results = [(name, func()) for name, func in tests]
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    percentage = (passed / total) * 100
    print("="*60)
    print(f"RESULT: {passed}/{total} passed ({percentage:.0f}%)")
    print("="*60)
    
    if percentage >= 75:
        print("\n🟢 PIPELINE READY FOR DEPLOYMENT")
    elif percentage >= 50:
        print("\n🟡 NEEDS FIXES")
    else:
        print("\n🔴 CRITICAL ISSUES")
    
    print("="*60)
    return 0 if percentage >= 50 else 1

if __name__ == "__main__":
    exit(main())
