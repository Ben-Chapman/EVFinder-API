from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")


@router.get("/inventory/kia")
async def get_kia_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """Makes a request to the Kia Inventory API and returns a JSON object containing
    the inventory results for a given vehicle model, zip code and search radius.
    Note: Kia returns all(?) available information for a vehicle in their inventory
    response, so there is no additional /vin/kia EV Finder API endpoint.
    """

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": (
            f"https://www.kia.com/us/en/inventory/result?zipCode={common_params.zip}"
            f"&seriesId={common_params.model}&year={common_params.year}"
        ),
    }

    # The Kia API operates via POST with the following data
    post_data = {
        "series": common_params.model,
        "year": common_params.year,
        "zipCode": common_params.zip,
        "status": ["DS", "IT"],  # Dealer stock, In Transit
        "selectedRange": common_params.radius,
        "currentRange": common_params.radius,
    }

    async with AsyncHTTPClient(
        base_url="https://www.kia.com", timeout_value=30.0
    ) as http:
        inv = await http.post(
            uri="/us/services/en/inventory/initial",
            headers=headers,
            post_data=post_data,
        )

        try:
            data = inv.json()
        except ValueError:
            return error_response(
                error_message="An error occurred obtaining Kia inventory results.",
                error_data=inv.text,
            )

    # When this key is not present, no vehicles were found for the given search so return
    # an empty dict instead of the Kia response (which is filled with nulls)
    try:
        data["inventoryVehicles"]
        return send_response(response_data=data)
    except KeyError:
        return send_response(response_data={})
