from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.http import AsyncHTTPClient
from src.libs.responses import error_response, send_response

router = APIRouter(prefix="/api")
kia_base_url = "https://www.kia.com"

# The Kia inventory API identifies each EV model by a three-letter series code. The UI
# sends the legacy single-letter model value (see CommonInventoryQueryParams), which is
# mapped here to the series code the inventory API now expects.
kia_series_codes = {
    "N": "NAE",  # EV6
    "V": "GAE",  # Niro EV
    "P": "PAE",  # EV9
}


@router.get("/inventory/kia")
async def get_kia_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """Makes a request to the Kia Inventory API and returns a JSON object containing
    the inventory results for a given vehicle model, zip code and search radius.
    """
    series = kia_series_codes.get(common_params.model, common_params.model)

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Origin": kia_base_url,
        "referer": (
            f"{kia_base_url}/us/en/inventory/result?zipCode={common_params.zip}"
            f"&seriesId={series}&year={common_params.year}"
        ),
    }

    # The Kia API operates via POST with the following data
    post_data = {
        "series": series,
        "year": common_params.year,
        "zipCode": common_params.zip,
        "status": ["DS", "IT"],  # Dealer stock, In Transit
        "selectedRange": common_params.radius,
        "currentRange": common_params.radius,
    }

    async with AsyncHTTPClient(base_url=kia_base_url, timeout_value=30.0) as http:
        inv = await http.post(
            uri="/us/services/en/inventory/initial",
            headers=headers,
            post_data=post_data,
        )

        try:
            data = inv.json()
        except ValueError:
            # A search for a year/model the Kia API does not recognize returns a 200
            # with a non-JSON error string rather than inventory. Treat it as no
            # inventory so the UI shows the "no inventory" message.
            return send_response(response_data={})

    # Return an empty dict (the UI's no-inventory signal) unless the response carries
    # both vehicles and dealers. A search with no inventory omits inventoryVehicles,
    # and a search whose radius contains no dealers returns nationwide near-matches
    # with an empty dealers list and null dealer fields, which the UI cannot render.
    if data.get("inventoryVehicles") and data.get("filterSet", {}).get("dealers"):
        return send_response(response_data=data)
    return send_response(response_data={})


@router.get("/vin/kia")
async def get_kia_vin_detail(req: Request) -> dict:
    """Makes a request to the Kia VIN detail API and returns the full detail for a
    single vehicle. The inventory API returns a slim record per vehicle, so the rich
    detail (engine, options, features, full color objects) is fetched here by VIN.
    """
    zip_code = req.query_params.get("zip")
    vin = req.query_params.get("vin")

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": (
            f"{kia_base_url}/us/en/inventory/vehicle-details"
            f"?vin={vin}&zipCode={zip_code}"
        ),
    }

    async with AsyncHTTPClient(base_url=kia_base_url, timeout_value=30.0) as http:
        v = await http.get(
            uri=f"/us/services/en/inventory/vinInfo/{zip_code}/{vin}",
            headers=headers,
        )

        try:
            vin_data = v.json()
        except ValueError:
            return error_response(
                error_message="An error occurred obtaining VIN detail for this vehicle.",
                error_data=v.text,
            )

    if vin_data.get("vehicles"):
        return send_response(response_data=vin_data)
    return error_response(
        error_message="An error occurred obtaining VIN detail for this vehicle.",
        error_data=vin_data,
        status_code=400,
    )
