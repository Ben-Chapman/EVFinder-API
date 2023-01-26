from fastapi import HTTPException
from typing import Optional


def error_response(
    error_message: str, error_data: Optional[dict] = None, status_code: int = 500
):
    """Return a standardized error response to the caller."""
    # Logging this error
    # logging.warning(f"{error_message}: {error_data}")

    return HTTPException(
        status_code=status_code,
        detail={"errorMessage": error_message, "errorData": error_data},
    )
