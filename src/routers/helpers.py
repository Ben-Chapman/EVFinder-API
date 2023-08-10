import os

from fastapi import APIRouter, Path

from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

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


@router.get("/test/status/{status_code}")
async def send_httpstatus_error_response(
    status_code: int = Path(
        title="A HTTP status code in the 400 or 500 class", ge=400, le=599
    ),
):
    async with AsyncHTTPClient(
        base_url="https://httpstat.us", timeout_value=1.0, verify=True
    ) as http:
        params = {"sleep": 2000}
        headers = {"User-Agent": "Test"}
        h = await http.get(uri=f"/{status_code}", params=params, headers=headers)

    try:
        h.json()
        return error_response(
            error_message=f"This is a error: {h}", status_code=status_code
        )
    except AttributeError:
        return error_response(
            error_message=f"This is a error: {h}", status_code=status_code
        )

    # return "foo"
    # return h.text if h.text else "foo"
    #
