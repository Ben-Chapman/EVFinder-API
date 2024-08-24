from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = True
chevrolet_base_url = "https://www.chevrolet.com/chevrolet/shopping/api"


@router.get("/inventory/chevrolet")
async def get_chevrolet_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """A description of what's unique about the logic for this manufacturer's API"""

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.chevrolet.com/shopping/inventory/search",
        "client": "T1_VSR",
        "tenantId": "0",
        "dealerId": "0",
        "oemId": "GM",
        "programId": "CHEVROLET",
    }

    inventory_post_data = {
        "filters": {
            "stockType": {"values": ["DealerStock"]},
            "year": {"values": [str(common_params.year)]},
            "model": {"values": [common_params.model.lower()]},
            "geo": {"zipCode": common_params.zip, "radius": common_params.radius},
        },
        "sort": {"name": "distance", "order": "ASC"},
        "paymentTypes": ["CASH"],
        "pagination": {"size": 100},
    }

    async with AsyncHTTPClient(
        base_url=chevrolet_base_url,
        timeout_value=30.0,
    ) as http:
        g = await http.post(
            uri="/aec-cp-discovery-api/p/v1/vehicles/search",
            headers=headers,
            post_data=inventory_post_data,
        )

    try:
        data = g.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Chevrolet inventory service: {g.text}"
        )

    error_message = "An error occurred with the Chevrolet inventory service"
    try:
        data["data"]["hits"]
        return send_response(
            response_data=data,
            cache_control_age=3600,
        )
    except KeyError:
        try:
            data["errorDetails"]["key"]
            return send_response(response_data={})
        except Exception:
            return error_response(error_message=error_message, error_data=data)


@router.get("/vin/chevrolet")
async def get_chevrolet_vin_detail(req: Request) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "client": "UI",
        "tenantId": "0",
        "dealerId": "0",
        "oemId": "GM",
        "programId": "CHEVROLET",
    }

    vin = req.query_params.get("vin")
    vin_post_data = {"vin": vin}

    async with AsyncHTTPClient(
        base_url=chevrolet_base_url,
        timeout_value=30.0,
        verify=verify_ssl,
    ) as http:
        g = await http.post(
            uri="/aec-cp-ims-apigateway/p/v1/vehicles/detail",
            headers=headers,
            post_data=vin_post_data,
        )
        data = g.json()

    try:
        vin_data = data["data"]["id"]
        return send_response(response_data=vin_data, cache_control_age=3600)
    except KeyError:
        error_message = f"""An error occurred with the Chevrolet inventory service when
        fetching VIN details for {vin}"""

        return error_response(error_message=error_message, error_data=data["data"])
