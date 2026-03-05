#!/usr/bin/env python3
"""Test rate limiter via HTTP with detailed debugging."""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001"
ENDPOINT = "/api/verify/github"

payload = {
    "username": "testuser",
    "claimed_skills": ["Python"]
}

print("=" * 70)
print("RATE LIMIT TEST - WITH DETAILED DEBUGGING")
print("=" * 70)

results = []
for i in range(1, 12):
    try:
        resp = requests.post(
            f"{BASE_URL}{ENDPOINT}",
            json=payload,
            timeout=2,
            headers={"Content-Type": "application/json"}
        )
        status = resp.status_code
        results.append(status)
        
        print(f"Request {i:2d}: Status {status}")
        if status == 429:
            print(f"           Rate limit hit! Response: {resp.json()}")
            break
        
        time.sleep(0.05)
    except Exception as e:
        print(f"Request {i:2d}: Exception - {str(e)[:60]}")

print(f"\nResults: {results}")
if 429 in results:
    idx = results.index(429) + 1
    print(f"✓ PASS: Rate limit triggered on request {idx}")
else:
    print(f"✗ FAIL: Rate limit not triggered, all returned {results[0]}")
