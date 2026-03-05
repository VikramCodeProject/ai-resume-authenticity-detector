#!/usr/bin/env python3
"""Test that verifies the Depends injection is being called by checking decorator approach instead."""
import sys
import asyncio
import os
sys.path.insert(0, 'backend')

def test_direct_import():
    """Verify imports work correctly."""
    try:
        print("1. Testing imports...")
        from api.routes import router
        print(f"   ✓ Router imported: {router}")
        print(f"   ✓ Routes in router: {[r.path for r in router.routes]}")
        
        # Find the verify/github endpoint
        github_route = None
        for route in router.routes:
            if hasattr(route, 'path') and '/verify/github' in route.path:
                github_route = route
                break
        
        if github_route:
            print(f"   ✓ Found /verify/github route: {github_route}")
            # Check if it has dependencies
            if hasattr(github_route, 'dependencies') and github_route.dependencies:
                print(f"   ✓ Route has {len(github_route.dependencies)} dependencies")
                for dep in github_route.dependencies:
                    print(f"     - {dep}")
            else:
                print(f"   ✗ Route has NO dependencies")
        else:
            print(f"   ✗ /verify/github route not found")
            
    except Exception as e:
        print(f"   ✗ Import error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_import()
