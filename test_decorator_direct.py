#!/usr/bin/env python3
"""Test SimpleRateLimiter.limit() decorator directly."""
import sys
sys.path.insert(0, 'backend')

import asyncio
from fastapi import Request, FastAPI
from utils.rate_limiter import limiter, RATE_LIMIT

app = FastAPI()

# Create a test endpoint with the limiter decorator
@limiter.limit(RATE_LIMIT)
async def test_endpoint(request: Request):
    return {"msg": "ok"}

# Simulate requests
async def test():
    print(f"limiter type: {type(limiter)}")
    print(f"limiter.limit_count: {limiter.limit_count}")
    print(f"limiter.limit_seconds: {limiter.limit_seconds}")
    print(f"RATE_LIMIT: {RATE_LIMIT}\n")
    
    # Create a mock request object
    class MockClient:
        host = "127.0.0.1"
    
    class MockRequest:
        def __init__(self, host="127.0.0.1"):
            self.client = MockClient()
            self.client.host = host
            self.headers = {}
    
    # Fire 11 requests
    print("Testing decorator with 11 requests:")
    for i in range(1, 12):
        mock_request = MockRequest()
        try:
            result = await test_endpoint(mock_request)
            print(f"Request {i:2d}: Success - {result}")
        except Exception as e:
            print(f"Request {i:2d}: Error - {type(e).__name__}: {str(e)[:50]}")

asyncio.run(test())
