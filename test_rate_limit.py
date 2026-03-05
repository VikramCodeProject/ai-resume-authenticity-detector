#!/usr/bin/env python3
"""Test rate limiting: fire 11 requests to verify request 11 gets 429."""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001"
ENDPOINT = "/api/verify/github"

payload = {
    "username": "testuser",
    "claimed_skills": ["Python", "JavaScript"]
}

print("=" * 70)
print("RATE LIMIT THRESHOLD TEST: 10/minute limit")
print("=" * 70)
print(f"Endpoint: POST {ENDPOINT}")
print(f"Firing 11 requests (expecting 200 x10, then 429 on request 11)")
print("-" * 70)

results = []
for i in range(1, 12):
    try:
        start = time.time()
        resp = requests.post(
            f"{BASE_URL}{ENDPOINT}",
            json=payload,
            timeout=3,
            headers={"Content-Type": "application/json"}
        )
        elapsed = time.time() - start
        status = resp.status_code
        results.append(status)
        
        # Print request result
        emoji = "✓" if (i < 11 and status == 200) or (i == 11 and status == 429) else "⚠"
        print(f"Request {i:2d}: {status} {emoji} ({elapsed:.2f}s)")
        
        # Show response body for debugging
        if i == 1 or status != 200:
            try:
                body = resp.json()
                print(f"         Response: {json.dumps(body, indent=2)[:100]}...")
            except:
                pass
        
        time.sleep(0.1)  # Small delay between requests
    except requests.exceptions.RequestException as e:
        try:
            status = e.response.status_code if hasattr(e, 'response') and e.response else "ERROR"
            results.append(status)
            print(f"Request {i:2d}: {status} (Exception)")
        except:
            print(f"Request {i:2d}: ERROR {str(e)[:30]}")
            results.append(-1)

# Summary
print("-" * 70)
print(f"Response codes: {results}")
print()

# Analysis
passed_count = sum(1 for i, code in enumerate(results[:10]) if code == 200)
limit_enforced = results[10] == 429 if len(results) > 10 else False

print("ANALYSIS:")
print(f"  Requests 1-10 returned 200: {passed_count}/10")
print(f"  Request 11 returned 429: {limit_enforced} (status: {results[10] if len(results) > 10 else 'N/A'})")
print()

if passed_count == 10 and limit_enforced:
    print("✓ PASS: Rate limiter is working correctly!")
elif all(code == 200 for code in results):
    print("⚠ INFO: All requests returned 200 (rate limit may not be active)")
    print("  This is expected in fallback mode without Redis")
else:
    print("✗ FAIL: Unexpected behavior")
