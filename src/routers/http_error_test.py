from fastapi import APIRouter, Path, Response
from libs.exceptions import error_response

router = APIRouter()


@router.get("/error/{status_code}")
def send_error_response(
    response: Response,
    status_code: int = Path(
        title="A HTTP status code in the 400 or 500 class", ge=400, le=599
    ),
):
    return error_response(
        error_message=f"This is a {status_code} error", status_code=status_code
    )