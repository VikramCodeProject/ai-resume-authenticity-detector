from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    payload: Dict[str, Any] = {
        "success": True,
        "data": data,
    }
    if meta:
        payload["meta"] = meta
    return JSONResponse(status_code=status_code, content=payload)


def error_response(message: str, code: int) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={
            "error": True,
            "message": message,
            "code": code,
        },
    )
