from fastapi import APIRouter, Depends, Request

from libs.common_query_params import CommonInventoryQueryParams
from libs.responses import error_response, send_response
from libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = True
chevrolet_base_url = "https://www.chevrolet.com/electric/shopping/api/drp-cp-api/p/v1"


@router.get("/inventory/chevrolet")
async def get_chevrolet_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """A description of what's unique about the logic for this manufacturer's API"""

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://chevrolet.com/referer/path",
    }

    inventory_post_data = {
        "name": "DrpInventory",
        "filters": [
            {
                "field": "model",
                "operator": "IN",
                "values": [common_params.model],
                "key": "model",
            },
            {
                "field": "year",
                "operator": "IN",
                "values": [common_params.year],
                "key": "year",
            },
            {
                "field": "radius",
                "operator": "IN",
                "values": [common_params.radius],
                "key": "radius",
            },
            {
                "field": "zipcode",
                "operator": "IN",
                "values": [common_params.zip],
                "key": "zipcode",
            },
        ],
        "sort": [{"field": "distance", "order": "ASC"}],
        "pageInfo": {"rows": 1000},
    }

    async with AsyncHTTPClient(
        base_url=chevrolet_base_url,
        timeout_value=30,
    ) as http:
        g = await http.post(
            uri="/vehicles",
            headers=headers,
            post_data=inventory_post_data,
        )

    try:
        data = g.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Chevrolet API: {g.text}"
        )
    try:
        # If the inventory request was successful, even if 0 vehicles are returned
        # the response will have the ['listResponse'] dict, so validating that
        data["data"]["listResponse"]
        return send_response(
            response_data=data,
            cache_control_age=3600,
        )
    except KeyError:
        print(data)
        error_message = "An error occurred with the Chevrolet API"
        return error_response(error_message=error_message, error_data=data)


@router.get("/vin/chevrolet")
async def get_chevrolet_vin_detail(req: Request) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
    }

    vin = req.query_params.get("vin")
    vin_post_data = {"key": "VIN", "value": vin}

    async with AsyncHTTPClient(
        base_url=chevrolet_base_url,
        timeout_value=30,
        verify=verify_ssl,
    ) as http:
        g = await http.post(
            uri="/vehicles/details",
            headers=headers,
            post_data=vin_post_data,
        )
        data = g.json()

    status_text = data.get("status")

    if status_text and status_text != "success":
        error_message = f"An error occurred with the Chevrolet API when fetching VIN details for {vin}"  # noqa: B950
        return error_response(error_message=error_message, error_data=data)

    return send_response(response_data=data, cache_control_age=3600)
