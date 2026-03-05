import os
import time
from collections import defaultdict
from fastapi import Request, HTTPException, Depends

# Force SlowAPIMiddleware to None since we're using native FastAPI approach
SlowAPIMiddleware = None
RateLimitExceeded = None  # Not needed with HTTPException

RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")
ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"


def api_key_or_ip(request: Request) -> str:
    """Get API key or IP address for rate limiting."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api_key:{api_key}"

    if request.client and request.client.host:
        return f"ip:{request.client.host}"

    # Fallback: try to get IP from X-Forwarded-For header
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    return "anonymous"


class SimpleRateLimiter:
    """Simple in-memory rate limiter that tracks request counts per key."""
    
    def __init__(self, rate_limit: str = "10/minute"):
        """Initialize limiter. Format: "10/minute", "100/hour", etc."""
        self.rate_limit = rate_limit
        self.request_history = defaultdict(list)  # key -> [timestamp, timestamp, ...]
        self.parse_limit(rate_limit)
    
    def parse_limit(self, rate_limit: str):
        """Parse rate limit string like '10/minute' into (count, seconds)."""
        parts = rate_limit.split("/")
        count = int(parts[0])
        period = parts[1].lower()
        
        time_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        
        seconds = time_map.get(period, 60)
        self.limit_count = count
        self.limit_seconds = seconds
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed, return True if within limit."""
        now = time.time()
        cutoff = now - self.limit_seconds
        
        # Clean old requests
        self.request_history[key] = [
            ts for ts in self.request_history[key] if ts > cutoff
        ]
        
        # Check if over limit
        count = len(self.request_history[key])
        is_over_limit = count >= self.limit_count
        
        # DEBUG: Log to file
        with open("rate_limit_debug.log", "a") as f:
            f.write(f"key={key}, count={count}, limit={self.limit_count}, allowed={not is_over_limit}\n")
        
        if is_over_limit:
            return False
        
        # Record this request
        self.request_history[key].append(now)
        return True


# Global limiter instance
limiter = SimpleRateLimiter(RATE_LIMIT)


async def check_rate_limit(request: Request):
    """FastAPI dependency for rate limiting (Depends injection)."""
    if not ENABLE_RATE_LIMITING:
        return
    
    key = api_key_or_ip(request)
    if not limiter.is_allowed(key):
        raise HTTPException(
            status_code=429,
            detail={
                "error": True,
                "message": "Too many requests. Please try again later.",
                "code": 429,
            },
        )


# Keep decorator method for backwards compatibility
def rate_limit_decorator(rate_limit_str: str):
    """Decorator wrapper (deprecated - use Depends instead)."""
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def async_wrapper(request: Request, *args, **kwargs):
            if not ENABLE_RATE_LIMITING:
                return await func(request, *args, **kwargs)
            
            key = api_key_or_ip(request)
            if not limiter.is_allowed(key):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": True,
                        "message": "Too many requests. Please try again later.",
                        "code": 429,
                    },
                )
            return await func(request, *args, **kwargs)
        
        return async_wrapper
    return decorator


async def rate_limit_exceeded_handler(request: Request, exc: Exception):
    """Handle rate limit exceeded errors"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "message": "Too many requests. Please try again later.",
            "code": 429,
        },
    )
