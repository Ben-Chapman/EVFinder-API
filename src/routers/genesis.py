from datetime import datetime

from fastapi import APIRouter, Depends, Path, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
refresh_token = datetime.now().isoformat(timespec="auto").split("T")[0]


@router.get("/{request_type}/genesis")
async def get_genesis_inventory(
    req: Request,
    common_params: CommonInventoryQueryParams = Depends(),
    request_type: str = Path(
        title="The type of request to make. Either dealer or inventory."
    ),
) -> dict:
    """Makes a request to the Genesis Inventory API and returns a JSON object containing
    the inventory results for a given vehicle model, zip code and search radius.
    """
    params = {
        "zip": common_params.zip,
        "year": common_params.year,
        "model": common_params.model,
        "radius": common_params.radius,
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": (
            "https://www.genesis.com"
            "/us/en/new/inventory/results"
            f"/year/{params['year']}/model/{params['model'].upper()}/zip/{params['zip']}"
        ),
    }

    async with AsyncHTTPClient(
        base_url="https://www.genesis.com", timeout_value=30, verify=False
    ) as http:
        if request_type == "inventory":
            inv = await http.get(
                uri=(
                    "/content/genesis/us/en/services/newinventory.js"
                    f"/model/{params['model']}/type/inventory/refreshToken/{refresh_token}.js"
                ),
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
        elif request_type == "dealer":
            # The Genesis inventory API does not contain detailed dealer information
            # just a dealer code. Making an additional call to their dealerservice
            # endpoint which does provide detailed dealer info (address, phone, etc).
            # The frontend will combine inventory and dealer results.
            # TODO: Eliminate this separate route, and combine into the /inventory route.
            # Both URLs always need to be called, and never together - so not much sense
            # in separate routes.
            dealers = await http.get(
                uri=(
                    "/content/genesis/us/en/services/dealerservice.js?"
                    "countryCode=en-US"
                    "&vehicleName=gOther"
                    f"&zipCode={params['zip']}"
                    "&noOfResults=300"
                    "&servicetype=new"
                    f"&year={params['year']}"
                    f"&refreshToken={refresh_token}"
                ),
                headers=headers,
            )
            dealer_data = dealers.json()

            if len(dealer_data) > 0:
                return send_response(
                    response_data=dealer_data,
                )
            else:
                error_message = "An error occurred with the Genesis API"
                return error_response(
                    error_message=error_message, error_data=dealer_data
                )
