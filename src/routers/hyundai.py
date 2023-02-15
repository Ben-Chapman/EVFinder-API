from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")


@router.get("/inventory/hyundai")
async def get_hyundai_inventory(
    req: Request, req_params: CommonInventoryQueryParams = Depends()
) -> dict:

    params = {
        "zip": req_params.zip,
        "year": req_params.year,
        "model": req_params.model.replace(" ", "-"),
        "radius": req_params.radius,
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.hyundaiusa.com/us/en/vehicles",
    }

    # Make a call to the Hyundai API
    async with AsyncHTTPClient(
        base_url="https://www.hyundaiusa.com", timeout_value=30, verify=False
    ) as http:
        g = await http.get(
            uri="/var/hyundai/services/inventory/vehicleList.json",
            headers=headers,
            params=params,
        )
        inventory = g.json()
        # Ensure the response back from the API has some status, indicating a successful
        # API call
        try:
            inventory["status"]
        except KeyError:
            return error_response(
                error_message="Invalid data received from the Hyundai API",
                error_data=inventory,
                status_code=500,
            )

        if "SUCCESS" in inventory["status"]:
            return send_response(response_data=inventory)
        else:
            return error_response(
                error_message="Received invalid data from the Hyundai API",
                error_data=inventory,
                status_code=400,
            )


@router.get("/vin")
@router.get("/vin/hyundai")
async def get_hyundai_vin_detail(req: Request) -> dict:

    # Make a call to the Hyundai API
    async with AsyncHTTPClient(
        base_url="https://www.hyundaiusa.com", timeout_value=30
    ) as http:
        params = {
            "model": req.query_params.get("model"),
            "year": req.query_params.get("year"),
            "vin": req.query_params.get("vin"),
            "brand": "hyundai",
        }
        headers = {
            "authority": "www.hyundaiusa.com",
            "User-Agent": req.headers.get("User-Agent"),
            "referer": (
                f"https://www.hyundaiusa.com/us/en/inventory-search/details?"
                f"model={params['model'].capitalize()}&year={params['year']}&vin={params['vin']}"
            ),
        }

        v = await http.get(
            uri="/var/hyundai/services/inventory/vehicleDetails.vin.json",
            headers=headers,
            params=params,
        )

        vin_data = v.json()

    if "SUCCESS" in vin_data["status"]:
        return send_response(response_data=vin_data)
    else:
        return error_response(
            error_message="Received invalid data from the Hyundai API",
            error_data=vin_data,
            status_code=400,
        )
