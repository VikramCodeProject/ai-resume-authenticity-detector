#!/usr/bin/env python3
"""Test rate limiter decorator."""
import sys
sys.path.insert(0, 'backend')

from utils.rate_limiter import limiter, RATE_LIMIT, simple_limiter

print(f'limiter type: {type(limiter)}')
print(f'limiter class name: {limiter.__class__.__name__}')
print(f'limiter has limit method: {hasattr(limiter, "limit")}')
print(f'RATE_LIMIT: {RATE_LIMIT}')

# Test the limit decorator directly
@limiter.limit(RATE_LIMIT)
async def test_func():
    return 'ok'

print(f'test_func: {test_func}')
print(f'test_func.__name__: {test_func.__name__}')

# Check simple_limiter state
print(f'\nsimple_limiter.request_history: {dict(simple_limiter.request_history)}')
print(f'simple_limiter.limit_count: {simple_limiter.limit_count}')
print(f'simple_limiter.limit_seconds: {simple_limiter.limit_seconds}')
