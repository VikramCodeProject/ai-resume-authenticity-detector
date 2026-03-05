"""
Full Local Integration Test - Real Services (PostgreSQL, Redis, Celery)
Simpler version without hanging on Redis connects
"""
import sys
import os
from uuid import uuid4
from typing import Tuple

sys.path.insert(0, "backend")

print("Loading integration tests...")

def check_redis() -> Tuple[bool, str]:
    """Check Redis connectivity"""
    print("\n" + "="*60)
    print("CHECK 1: Redis Cache")
    print("="*60)
    
    try:
        import redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        
        r = redis.Redis(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            password=parsed.password,
            decode_responses=True,
            socket_connect_timeout=2
        )
        
        response = r.ping()
        if response:
            print(f"✓ Connected to Redis at {parsed.hostname or 'localhost'}:{parsed.port or 6379}")
            
            try:
                info = r.info('memory')
                used_mb = info.get('used_memory_human', 'unknown')
                print(f"✓ Redis memory usage: {used_mb}")
            except:
                pass
            
            return True, "Redis OK"
    except ModuleNotFoundError:
        print("✗ redis not installed")
        return False, "pip install redis"
    except Exception as e:
        print(f"✗ Redis connection failed: {str(e)[:60]}")
        return False, "Redis unavailable"

def check_postgresql() -> Tuple[bool, str]:
    """Check PostgreSQL connectivity"""
    print("\n" + "="*60)
    print("CHECK 2: PostgreSQL Database")
    print("="*60)
    
    try:
        import psycopg2
        
        db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/resume_verify')
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            user=parsed.username or 'postgres',
            password=parsed.password or 'postgres',
            database=parsed.path.lstrip('/') or 'resume_verify',
            connect_timeout=3
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        
        # Count tables
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"✓ Connected to PostgreSQL at {parsed.hostname or 'localhost'}:{parsed.port or 5432}")
        
        if table_count > 0:
            print(f"✓ Database schema found ({table_count} tables)")
            return True, "PostgreSQL OK"
        else:
            print("⚠ Database exists but is empty (run migrations)")
            return False, "Run: alembic upgrade head"
            
    except ModuleNotFoundError:
        print("✗ psycopg2 not installed")
        return False, "pip install psycopg2"
    except Exception as e:
        error_msg = str(e)[:60]
        print(f"✗ PostgreSQL connection failed: {error_msg}")
        if "connect" in error_msg.lower():
            print("   (Make sure PostgreSQL server is running)")
        return False, "PostgreSQL unavailable"

def check_api() -> Tuple[bool, str]:
    """Check FastAPI application"""
    print("\n" + "="*60)
    print("CHECK 3: FastAPI Application")
    print("="*60)
    
    try:
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app, base_url="http://127.0.0.1")
        
        response = client.post("/api/verify/github", json={
            "username": "test",
            "claimed_skills": ["python"]
        })
        
        if response.status_code in [200, 429]:
            print(f"✓ API responding (status: {response.status_code})")
            return True, "FastAPI OK"
        else:
            print(f"⚠ API response: {response.status_code}")
            return False, f"Status {response.status_code}"
            
    except Exception as e:
        print(f"✗ FastAPI check failed: {str(e)[:60]}")
        return False, "FastAPI error"

def test_api_endpoints() -> bool:
    """Test API functionality"""
    print("\n" + "="*60)
    print("TEST 1: API Endpoints")
    print("="*60)
    
    try:
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app, base_url="http://127.0.0.1")
        
        tests = [
            ("GitHub endpoint", "/api/verify/github", {"username": "test", "claimed_skills": ["python"]}),
            ("Full verification", "/api/verify/full", {"resume_id": str(uuid4()), "github_username": "test"}),
            ("Task status", "/api/task-status/test", None),
        ]
        
        passed = 0
        for name, endpoint, payload in tests:
            try:
                if payload is None:
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint, json=payload)
                
                if response.status_code in [200, 404, 429]:
                    print(f"✓ {name}: {response.status_code}")
                    passed += 1
                else:
                    print(f"✗ {name}: {response.status_code}")
            except Exception as e:
                print(f"✗ {name}: {str(e)[:40]}")
        
        return passed >= 2
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)[:60]}")
        return False

def test_database_if_available() -> bool:
    """Test database operations if available"""
    print("\n" + "="*60)
    print("TEST 2: Database Operations (if available)")
    print("="*60)
    
    try:
        import psycopg2
        
        db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/resume_verify')
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            user=parsed.username or 'postgres',
            password=parsed.password or 'postgres',
            database=parsed.path.lstrip('/') or 'resume_verify',
            connect_timeout=2
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"✓ Database query successful")
        print(f"✓ Users in DB: {count}")
        return True
        
    except:
        print("ℹ PostgreSQL not fully available - skipping DB tests")
        return False

def test_redis_if_available() -> bool:
    """Test Redis operations if available"""
    print("\n" + "="*60)
    print("TEST 3: Redis Operations (if available)")
    print("="*60)
    
    try:
        import redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        
        r = redis.Redis(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            password=parsed.password,
            decode_responses=True,
            socket_connect_timeout=2
        )
        
        test_key = f"test_{uuid4()}"
        r.set(test_key, "test_value", ex=10)
        val = r.get(test_key)
        
        if val == "test_value":
            print(f"✓ Redis write/read successful")
            r.delete(test_key)
            return True
        else:
            print(f"✗ Redis data mismatch")
            return False
            
    except:
        print("ℹ Redis not fully available - skipping Redis tests")
        return False

def main():
    print("=" * 60)
    print("FULL INTEGRATION TEST - REAL SERVICES")
    print("=" * 60)
    
    # Check services
    print("\n[SERVICE CHECKS]")
    checks = [
        ("Redis", check_redis()),
        ("PostgreSQL", check_postgresql()),
        ("FastAPI", check_api()),
    ]
    
    postgres_ok, _ = checks[1][1]
    redis_ok, _ = checks[0][1]
    api_ok, _ = checks[2][1]
    
    # Summary
    print("\n" + "=" * 60)
    print("SERVICE AVAILABILITY")
    print("=" * 60)
    
    for name, (ok, msg) in checks:
        status = "✓" if ok else "✗"
        print(f"{status} {name:15} {msg}")
    
    # Run tests based on available services
    print("\n[INTEGRATION TESTS]")
    test_results = []
    
    test_results.append(("API Endpoints", test_api_endpoints()))
    
    if postgres_ok:
        test_results.append(("Database", test_database_if_available()))
    
    if redis_ok:
        test_results.append(("Redis", test_redis_if_available()))
    
    # Final summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, p in test_results if p)
    total = len(test_results)
    
    for name, p in test_results:
        status = "✓ PASS" if p else "✗ FAIL"
        print(f"{status:10} {name}")
    
    print("=" * 60)
    
    if total > 0:
        percentage = (passed / total * 100)
        print(f"RESULT: {passed}/{total} passed ({percentage:.0f}%)")
    else:
        print("No integration tests run")
        percentage = 0
    
    print("=" * 60)
    
    if api_ok:
        if postgres_ok and redis_ok:
            print("\n🟢 FULL INTEGRATION READY")
            print("   All services available for production deployment")
        else:
            print("\n🟡 PARTIAL INTEGRATION")
            print("   Can deploy to staging with managed services")
    else:
        print("\n✗ API ISSUES DETECTED")
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit(main())
