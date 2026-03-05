#!/usr/bin/env python3
"""Check rate limiting settings."""
import sys
import os
sys.path.insert(0, 'backend')

from utils.rate_limiter import limiter, ENABLE_RATE_LIMITING, RATE_LIMIT

print(f"ENABLE_RATE_LIMITING: {ENABLE_RATE_LIMITING}")
print(f"RATE_LIMIT: {RATE_LIMIT}")
print(f"limiter type: {type(limiter).__name__}")
print(f"limiter.limit_count: {limiter.limit_count}")
print(f"limiter.limit_seconds: {limiter.limit_seconds}")
print(f"limiter.request_history: {dict(limiter.request_history)}")

# Check environment
print(f"\nEnvironment variables:")
print(f"  ENABLE_RATE_LIMITING env: {os.getenv('ENABLE_RATE_LIMITING')}")
print(f"  RATE_LIMIT env: {os.getenv('RATE_LIMIT')}")
