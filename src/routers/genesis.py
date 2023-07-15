from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = True
genesis_base_url = "https://www.genesis.com"


@router.get("/inventory/genesis")
async def get_genesis_inventory(
    req: Request,
    common_params: CommonInventoryQueryParams = Depends(),
) -> dict:
    """Makes a request to the Genesis Inventory API and returns a JSON object containing
    the inventory results for a given vehicle model, zip code and search radius.
    """
    params = {
        "zip": common_params.zip,
        "year": common_params.year,
        "modelname": common_params.model,
        "radius": common_params.radius,
        "maxdealers": 25,
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": f"{genesis_base_url}/us/en/new/inventory.html",
    }

    async with AsyncHTTPClient(
        base_url=genesis_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        inv = await http.get(
            uri=("/bin/api/v1/inventory"),
            headers=headers,
            params=params,
        )

        inventory_data = inv.json()

        if len(inventory_data) > 0:
            return send_response(
                response_data=inventory_data,
            )
        else:
            error_message = "An error occurred with the Genesis API"
            return error_response(
                error_message=error_message, error_data=inventory_data
            )


@router.get("/vin/genesis")
async def get_genesis_vin_detail(req: Request) -> dict:
    vin_params = {
        "zip": req.query_params.get("zip"),
        "vin": req.query_params.get("vin"),
    }

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": f"{genesis_base_url}/us/en/new/inventory.html?vin={vin_params['vin']}",
    }

    async with AsyncHTTPClient(
        base_url=genesis_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        v = await http.get(
            uri=("/bin/api/v1/vehicledetails.json"),
            headers=headers,
            params=vin_params,
        )

        vin_data = v.json()

        if len(vin_data) > 0:
            return send_response(
                response_data=vin_data,
            )
        else:
            error_message = "An error occurred with the Genesis API"
            return error_response(error_message=error_message, error_data=vin_data)
