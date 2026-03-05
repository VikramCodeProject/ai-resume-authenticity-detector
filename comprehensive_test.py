#!/usr/bin/env python3
"""Comprehensive rate limiter test."""
import sys
sys.path.insert(0, 'backend')

import asyncio
from fastapi import Request#, FastAPI
from utils.rate_limiter import limiter, api_key_or_ip

# Test 1: Test api_key_or_ip directly
print("=" * 70)
print("TEST 1: api_key_or_ip extraction")
print("=" * 70)

class MockConnection:
    def __init__(self, host):
        self.host = host

class MockRequest:
    def __init__(self, host="192.168.1.100"):
        self.client = MockConnection(host)
        self.headers = {}

req = MockRequest("127.0.0.1")
key = api_key_or_ip(req)
print(f"Extracted key: {key}")
print(f"Expected: ip:127.0.0.1")
print()

# Test 2: Test is_allowed directly
print("=" * 70)
print("TEST 2: SimpleRateLimiter.is_allowed()")
print("=" * 70)

test_key = "ip:127.0.0.1"
for i in range(1, 12):
    allowed = limiter.is_allowed(test_key)
    count = len(limiter.request_history[test_key])
    print(f"Request {i:2d}: allowed={allowed}, count={count}")
    if not allowed:
        print("  ^ Rate limit hit!")
        break

print()

# Test 3: Test decorator with mock request
print("=" * 70)
print("TEST 3: Decorator with mock FastAPI Request")
print("=" * 70)

# Reset limiter state
limiter.request_history.clear()

# Create a real FastAPI test client
from fastapi import FastAPI
from starlette.testclient import TestClient

app = FastAPI()

@app.post("/test")
@limiter.limit("5/minute")
async def test_endpoint(request: Request):
    return {"status": "ok"}

# Use TestClient for proper request simulation
client = TestClient(app)

print("Sending 7 requests (expecting 5x200, then 2x429):\n")
for i in range(1, 8):
    response = client.post("/test")
    if response.status_code == 429:
        print(f"Request {i}: {response.status_code} (Rate limited) ✓")
    else:
        print(f"Request {i}: {response.status_code}")
