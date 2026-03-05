"""Test to check slowapi functionality."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get('/test')
@limiter.limit('2/minute')
def test_endpoint(request: Request):
    return {'msg': 'ok'}

# Manually check if decorator is applied
endpoint_func = test_endpoint
print(f'Endpoint function: {endpoint_func}')
print(f'Has __wrapped__: {hasattr(endpoint_func, "__wrapped__")}')
print(f'Function name: {endpoint_func.__name__}')

# Try to find the limiter
if hasattr(endpoint_func, '__self__'):
    print('Has __self__')
if hasattr(endpoint_func, '__closure__'):
    print(f'Closure length: {len(endpoint_func.__closure__) if endpoint_func.__closure__ else 0}')

print("\nLimiter info:")
print(f'Limiter type: {type(limiter)}')
print(f'Limiter key_func: {limiter.key_func}')
