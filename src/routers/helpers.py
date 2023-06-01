import os

from fastapi import APIRouter, Path

from libs.responses import error_response, send_response

router = APIRouter(prefix="/api")
verify_ssl = True


@router.get("/version")
async def get_manufacturer_inventory():
    """Returns the currently deployed version of the EV Finder API. The API version is
    obtained through a Cloud Run environment variable set during the build  process.
    """
    v = {"apiVersion": os.environ.get("VERSION")}
    return send_response(v)


@router.get("/test/error/{status_code}")
def send_error_response(
    status_code: int = Path(
        title="A HTTP status code in the 400 or 500 class", ge=400, le=599
    ),
):
    """This endpoint is used by the frontend Cypress tests to validate error handling in
    the Vue app
    """
    return error_response(
        error_message=f"This is a {status_code} error", status_code=status_code
    )
