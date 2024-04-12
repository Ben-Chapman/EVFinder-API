from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = True
hyundai_base_url = "https://www.hyundaiusa.com"


@router.get("/inventory/hyundai")
async def get_hyundai_inventory(
    req: Request, req_params: CommonInventoryQueryParams = Depends()
) -> dict:
    params = {
        "zip": req_params.zip,
        "year": req_params.year,
        "model": req_params.model.replace("%20", "-"),
        "radius": req_params.radius,
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.hyundaiusa.com/us/en/vehicles",
    }

    # Make a call to the Hyundai API
    async with AsyncHTTPClient(
        base_url=hyundai_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        g = await http.get(
            uri="/var/hyundai/services/inventory/vehicleList.json",
            headers=headers,
            params=params,
        )
    try:
        inventory = g.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Hyundai API: {g.text}"
        )
    # Ensure the response back from the API has some status, indicating a successful
    # API call
    try:
        inventory["status"]
    except KeyError:
        return error_response(
            error_message="An error occurred obtaining vehicle inventory for this search.",
            error_data=inventory,
            status_code=500,
        )

    if "SUCCESS" in inventory["status"]:
        return send_response(response_data=inventory)
    else:
        try:
            error_message = inventory.text
        except AttributeError:
            error_message = inventory["status"]

        return error_response(
            error_message="An error occurred obtaining vehicle inventory for this search.",
            error_data=error_message,
            status_code=400,
        )


@router.get("/vin")
@router.get("/vin/hyundai")
async def get_hyundai_vin_detail(req: Request) -> dict:
    # Make a call to the Hyundai API
    async with AsyncHTTPClient(
        base_url=hyundai_base_url, timeout_value=30.0, verify=verify_ssl
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
                f"{hyundai_base_url}/us/en/inventory-search/details?"
                f"model={params['model'].capitalize()}&year={params['year']}&vin={params['vin']}"
            ),
        }

        v = await http.get(
            uri="/var/hyundai/services/inventory/vehicleDetails.vin.json",
            headers=headers,
            params=params,
        )

        try:
            vin_data = v.json()
        except AttributeError:
            return error_response(error_message=v, status_code=504)
        else:
            if "SUCCESS" in vin_data["status"]:
                return send_response(response_data=vin_data)
            else:
                return error_response(
                    error_message="An error occurred obtaining VIN detail for this vehicle.",
                    error_data=vin_data,
                    status_code=400,
                )
