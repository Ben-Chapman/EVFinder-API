from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.exceptions import error_response
from src.libs.http import AsyncHTTPClient, send_response

router = APIRouter(prefix="/api")


@router.get("/inventory/hyundai")
async def testing(
    req: Request, req_params: CommonInventoryQueryParams = Depends()
) -> dict:
    # api_url = (
    #     "https://www.hyundaiusa.com/var/hyundai/services/inventory/vehicleList.json"
    # )
    params = {
        "zip": req_params.zip,
        "year": req_params.year,
        "model": "Ioniq%205",
        "radius": req_params.radius,
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.hyundaiusa.com/us/en/vehicles",
    }

    # Make a call to the Hyundai API
    async with AsyncHTTPClient(
        base_url="https://www.hyundaiusa.com", timeout_value=30
    ) as http:
        g = await http.get(
            uri="/var/hyundai/services/inventory/vehicleList.json",
            headers=headers,
            params=params,
        )
        data = g.json()

        # Ensure the response back from the API has some status, indicating a successful
        # API call
        try:
            data["status"]
        except KeyError:
            return error_response(
                error_message="Invalid data received from the Hyundai API",
                error_data=data,
                status_code=500,
            )

        if "SUCCESS" in data["status"]:
            return send_response(response_data=data)
        else:
            return error_response(
                error_message="Received invalid data from the Hyundai API",
                error_data=data,
                status_code=400,
            )
