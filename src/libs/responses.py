from fastapi import HTTPException
from fastapi.responses import JSONResponse


def send_response(
    response_data: dict,
    cache_control_age: int = 3600,
    status_code: int = 200,
):
    """Return a valid JSON response to the caller."""
    headers = {
        "Cache-Control": f"public, max-age={str(cache_control_age)}, immutable",
    }
    return JSONResponse(content=response_data, headers=headers, status_code=status_code)


def error_response(
    error_message: str, error_data: dict | None = None, status_code: int = 500
):
    """Return a standardized error response to the caller."""
    # Logging this error
    # logging.warning(f"{error_message}: {error_data}")

    raise HTTPException(
        status_code=status_code,
        detail={"errorMessage": error_message, "errorData": error_data},
    )
