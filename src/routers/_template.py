from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")

###
# This is a generalized template which can be used when building a new EV Finder API
# endpoint in support of a new EV manufacturer. How to modify this template should
# hopefully be self-explanatory, but in short:
# - Copy this file to <manufacturer>.py in the routers directory
# - Replace "manufacturer" throughout this file to reflect the new manufacturer's
#   details.
# - You will likely need to add additional logic to deal with the specifics for each
#   manufacturer. This is simply a skeleton framework to help get you started.
# - Review other manufacturer's implementations for insight/inspiration.
###


@router.get("/inventory/manufacturer")
async def get_MANUFACTURER_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """A description of what's unique about the logic for this manufacturer's API"""
    params = {
        "zip": common_params.zip,
        "year": common_params.year,
        "model": common_params.model,
        "radius": common_params.radius,
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://manufacturer.com/referer/path",
    }

    async with AsyncHTTPClient(
        base_url="https://www.manufacturer.com", timeout_value=30
    ) as http:
        g = await http.get(
            uri="/path/to/manufacturer/inventory/api/endpoint",
            headers=headers,
            params=params,
        )
        data = g.json()

        # Logic here to validate that we have a successful API response back from the
        # manufacturer. Validation of the response status code is often not enough.
        try:
            data["status"]
        except KeyError:
            return error_response(
                error_message="Invalid data received from the Manufacturer API",
                error_data=data,
                status_code=500,
            )

        # Logic here to validate that the API response back from the manufacturer was
        # successful. Adjust as needed
        if "SUCCESS" in data["status"]:
            return send_response(response_data=data)
        else:
            return error_response(
                error_message="Received invalid data from the Manufacturer API",
                error_data=data,
                status_code=400,
            )
