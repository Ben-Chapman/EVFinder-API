from fastapi import APIRouter, Depends, Request

from libs.common_query_params import CommonInventoryQueryParams
from libs.responses import error_response, send_response
from libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = True
manufacturer_base_url = ""


@router.get("/inventory/manufacturer")
async def get_manufacturer_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """A description of what's unique about the logic for this manufacturer's API"""

    # zip_code = common_params.zip
    # year = common_params.year
    # model = common_params.model
    # radius = common_params.radius

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
    }

    async with AsyncHTTPClient(
        base_url=manufacturer_base_url, timeout_value=30, verify=verify_ssl
    ) as http:
        g = await http.get(
            uri="",
            headers=headers,
            params="",
        )

    try:
        data = g.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Manufacturer API: {g.text}"
        )
    try:
        # Some validation that the API response was successful
        data["data"]
        return send_response(
            response_data=data,
            cache_control_age=3600,
        )
    except KeyError:
        print(data)
        error_message = "An error occurred with the Manufacturer API"
        return error_response(error_message=error_message, error_data=data)


@router.get("/vin/manufacturer")
async def get_manufacturer_vin_detail(req: Request) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
    }

    # vin = req.query_params.get("vin")

    async with AsyncHTTPClient(
        base_url=manufacturer_base_url,
        timeout_value=30,
        verify=verify_ssl,
    ) as http:
        v = await http.get(uri="", headers=headers, params="")
        data = v.json()

    return send_response(response_data=data, cache_control_age=3600)
