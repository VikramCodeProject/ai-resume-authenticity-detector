#!/usr/bin/env python3
"""Verify limiter decorator is applied to routes."""
import sys
sys.path.insert(0, 'backend')

from api.routes import verify_github_endpoint
from utils.rate_limiter import limiter

print(f"verify_github_endpoint: {verify_github_endpoint}")
print(f"verify_github_endpoint.__name__: {verify_github_endpoint.__name__}")
print(f"Type: {type(verify_github_endpoint)}")

# Check closure to see if decorator was applied
if hasattr(verify_github_endpoint, '__closure__'):
    print(f"Has closure: True")
    if verify_github_endpoint.__closure__:
        print(f"Closure cells: {len(verify_github_endpoint.__closure__)}")
        for i, cell in enumerate(verify_github_endpoint.__closure__):
            try:
                val = cell.cell_contents
                print(f"  Cell {i}: {type(val).__name__} - {str(val)[:80]}")
            except:
                pass
else:
    print("Has closure: False")

# Check if 'is_allowed' or 'SimpleRateLimiter' appears in the source
import inspect
try:
    source = inspect.getsource(verify_github_endpoint)
    if 'is_allowed' in source:
        print("\n✓ Found 'is_allowed' in source - decorator is applied!")
    else:
        print("\n✗ 'is_allowed' NOT in source - decorator may not be applied correctly")
except:
    print("Could not get source")
