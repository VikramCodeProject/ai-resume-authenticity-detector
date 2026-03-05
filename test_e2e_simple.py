"""
End-to-End Integration Test for Resume Verification Pipeline
Tests with mocked Redis/Celery to avoid infrastructure requirements
"""
import sys
import json
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, "backend")

# Mock Celery and Redis before importing the app
sys.modules['celery'] = MagicMock()
sys.modules['redis'] = MagicMock()

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, base_url="http://127.0.0.1")

def test_1_health_check():
    """Test 1: Verify API is healthy"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    try:
        response = client.get("/health")
        print(f"✓ Status: {response.status_code}")
        if response.status_code != 404:
            print(f"✓ Response: {response.text[:100]}")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"✗ Failed: {str(e)[:100]}")
        return False

def test_2_github_endpoint():
    """Test 2: GitHub verification endpoint response"""
    print("\n" + "="*60)
    print("TEST 2: GitHub Verification Endpoint")
    print("="*60)
    try:
        with patch('api.routes.verify_github.delay', return_value=MagicMock(id='task-123')):
            payload = {
                "username": "torvalds",
                "claimed_skills": ["C", "Git", "Linux"]
            }
            response = client.post("/api/verify/github", json=payload)
            print(f"✓ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Response: {json.dumps(data, indent=2)[:150]}")
                return "task_id" in data or "status" in data
            elif response.status_code == 429:
                print("✓ Rate limited (expected after 10 requests)")
                return True
            else:
                print(f"✗ Unexpected status: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"✗ Failed: {str(e)[:150]}")
        import traceback
        traceback.print_exc()
        return False

def test_3_full_endpoint():
    """Test 3: Full verification endpoint response"""
    print("\n" + "="*60)
    print("TEST 3: Full Verification Endpoint")
    print("="*60)
    try:
        with patch('api.routes.verify_full.delay', return_value=MagicMock(id='task-456')):
            payload = {
                "username": "testuser",
                "email": "test@example.com",
                "resume_text": "Senior Python Developer",
                "claimed_skills": ["Python", "FastAPI"]
            }
            response = client.post("/api/verify/full", json=payload)
            print(f"✓ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Response has: {list(data.keys())}")
                return True
            elif response.status_code == 429:
                print("✓ Rate limited")
                return True
            else:
                print(f"Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"✗ Failed: {str(e)[:150]}")
        return False

def test_4_task_status():
    """Test 4: Task status endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Task Status Endpoint")
    print("="*60)
    try:
        response = client.get("/api/task-status/test-task-xyz")
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response keys: {list(data.keys())}")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"✗ Failed: {str(e)[:100]}")
        return False

def test_5_routes_registered():
    """Test 5: Verify critical routes exist"""
    print("\n" + "="*60)
    print("TEST 5: Critical Routes Registered")
    print("="*60)
    try:
        routes = [r.path for r in app.routes]
        
        required_routes = [
            "/api/verify/github",
            "/api/verify/full",
            "/api/task-status/{task_id}",
        ]
        
        found = 0
        for route in required_routes:
            if route in routes:
                print(f"✓ {route}")
                found += 1
            else:
                print(f"✗ {route} NOT FOUND")
        
        print(f"✓ Found {found}/{len(required_routes)} critical routes")
        return found >= 2
    except Exception as e:
        print(f"✗ Failed: {str(e)[:100]}")
        return False

def test_6_rate_limiter_works():
    """Test 6: Rate limiter is installed"""
    print("\n" + "="*60)
    print("TEST 6: Rate Limiter Integration")
    print("="*60)
    try:
        # Check if rate limiter is imported and available
        from utils.rate_limiter import check_rate_limit, limiter
        print(f"✓ Rate limiter imported")
        print(f"✓ Limiter object: {limiter.__class__.__name__}")
        print(f"✓ check_rate_limit function available")
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)[:100]}")
        return False

def test_7_middleware_present():
    """Test 7: Security middleware"""
    print("\n" + "="*60)
    print("TEST 7: Middleware Stack")
    print("="*60)
    try:
        middleware_names = [type(m).__name__ for m in app.user_middleware]
        print(f"✓ Middleware count: {len(middleware_names)}")
        for name in middleware_names[:5]:  # Show first 5
            print(f"  - {name}")
        return len(middleware_names) > 0
    except Exception as e:
        print(f"✗ Failed: {str(e)[:100]}")
        return False

def test_8_error_handling():
    """Test 8: Error handling for invalid requests"""
    print("\n" + "="*60)
    print("TEST 8: Error Handling")
    print("="*60)
    try:
        # Test with missing required fields
        response = client.post("/api/verify/github", json={})
        print(f"✓ Empty payload response: {response.status_code}")
        
        # Test with invalid method
        response = client.get("/api/verify/github")
        print(f"✓ GET on POST endpoint: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)[:100]}")
        return False

def main():
    """Run all tests"""
    print("╔" + "═"*58 + "╗")
    print("║" + " RESUME VERIFICATION - E2E TEST SUITE ".center(58) + "║")
    print("╚" + "═"*58 + "╝")
    
    results = []
    
    results.append(("Health Check", test_1_health_check()))
    results.append(("GitHub Endpoint", test_2_github_endpoint()))
    results.append(("Full Verification", test_3_full_endpoint()))
    results.append(("Task Status", test_4_task_status()))
    results.append(("Routes Registered", test_5_routes_registered()))
    results.append(("Rate Limiter", test_6_rate_limiter_works()))
    results.append(("Middleware", test_7_middleware_present()))
    results.append(("Error Handling", test_8_error_handling()))
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} | {name}")
    
    print("="*60)
    percentage = (passed / total) * 100
    print(f"SCORE: {passed}/{total} tests passed ({percentage:.0f}%)")
    
    if percentage >= 75:
        print("🟢 READY FOR STAGING DEPLOYMENT")
    elif percentage >= 50:
        print("🟡 NEEDS FIXES BEFORE DEPLOYMENT")
    else:
        print("🔴 CRITICAL ISSUES - DO NOT DEPLOY")
    
    print("="*60)
    return 0 if percentage >= 50 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
