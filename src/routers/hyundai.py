from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.http import AsyncHTTPClient
from src.libs.responses import error_response, send_response

router = APIRouter(prefix="/api")
verify_ssl = True
hyundai_base_url = "https://www.hyundaiusa.com"

# Hyundai retired the legacy vehicleList.json inventory feed. Inventory now comes
# from the BSI search API, which returns a flat, paginated list of vehicles carrying
# all of the detail the UI needs (price, colors, drivetrain, delivery date).
bsi_base_url = "https://papp-bsi-api.hyundaiusa.com"

# The BSI search API identifies models by an internal code rather than a name. Keys
# are the normalized model value sent by the UI (see normalize_model).
hyundai_model_codes = {
    "ioniq 5": "5004",
    "ioniq 5 n": "5008",
    "ioniq 6": "A004",
    "ioniq 9": "7004",
    "kona ev": "Q004",
}

# The BSI search API caps the page size at 30 regardless of the requested value.
bsi_page_size = 30

# Each BSI vehicle record carries large blobs the inventory UI never uses (full
# spec sheets, feature lists, 360 image sets). Project each record down to just the
# fields the UI renders to keep response sizes small.
bsi_vehicle_fields = (
    "vin",
    "modelYear",
    "model",
    "trim",
    "msrp",
    "exteriorColor",
    "exteriorColorCode",
    "interiorColor",
    "interiorColorCode",
    "drivetrain",
    "drivetrainName",
    "plannedDeliveryDate",
    "inventoryStatusCode",
    "dealerName",
    "dealerAddress",
    "dealerCode",
    "distanceFromOrigin",
)


def slim_vehicle(vehicle: dict) -> dict:
    """Project a BSI vehicle record down to the fields the inventory UI renders.

    Args:
        vehicle: A single vehicle record from the BSI search response.

    Returns:
        A dict containing only the fields in bsi_vehicle_fields that are present.
    """
    return {key: vehicle[key] for key in bsi_vehicle_fields if key in vehicle}


def normalize_model(model: str) -> str:
    """Normalize a UI model value into a hyundai_model_codes lookup key.

    The UI sends models in a few formats (e.g. "Ioniq%205", "Ioniq-5-N"). This
    collapses separators and casing so they map to a single key.

    Args:
        model: The raw model value from the inventory query parameters.

    Returns:
        The normalized lookup key.
    """
    return model.replace("%20", " ").replace("-", " ").strip().lower()


@router.get("/inventory/hyundai")
async def get_hyundai_inventory(
    req: Request, req_params: CommonInventoryQueryParams = Depends()
) -> dict:
    model_code = hyundai_model_codes.get(normalize_model(req_params.model))
    if model_code is None:
        return error_response(
            error_message=(
                f"The model '{req_params.model}' is not a supported Hyundai model."
            ),
            status_code=400,
        )

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Content-Type": "application/json",
        "Origin": hyundai_base_url,
        "Referer": f"{hyundai_base_url}/",
    }

    def build_body(page: int) -> dict:
        return {
            "zipCode": req_params.zip,
            "distance": req_params.radius,
            "page": page,
            "pageSize": bsi_page_size,
            "modelYear": [req_params.year] if req_params.year else [],
            "modelName": [{"code": model_code, "trims": []}],
            "sort": {"attributeName": "distance", "order": "asc"},
        }

    # Make a call to the Hyundai BSI search API
    async with AsyncHTTPClient(
        base_url=bsi_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        first = await http.post(
            uri="/inventory/item/v2/search",
            headers=headers,
            post_data=build_body(1),
        )
        try:
            payload = first.json()
        except ValueError:
            return error_response(
                error_message=f"An error occurred with the Hyundai API: {first.text}"
            )

        data = payload.get("data") or {}
        vehicles = [slim_vehicle(v) for v in data.get("items") or []]
        total_pages = data.get("totalPages") or 1

        # Fetch any remaining pages in parallel. The API caps pageSize at 30, so a
        # dense search can span many pages; issue them concurrently rather than
        # serially. Passing a list of [uri, headers, post_data] to http.post fetches
        # every page at once.
        if total_pages > 1:
            urls_to_fetch = [
                ["/inventory/item/v2/search", headers, build_body(page)]
                for page in range(2, total_pages + 1)
            ]
            remainder = await http.post(uri=urls_to_fetch)

            # A single remaining page returns one Response; normalize to a list.
            if type(remainder) is not list:
                remainder = [remainder]

            for api_result in remainder:
                try:
                    page_data = api_result.json().get("data") or {}
                except AttributeError, ValueError:
                    continue
                vehicles.extend(slim_vehicle(v) for v in page_data.get("items") or [])

    # If no vehicles were returned, there is no inventory. Return an empty dict
    # response which the UI uses to display the no inventory message. This most
    # commonly occurs when the user selects a year that is not valid for a model.
    if not vehicles:
        return send_response(response_data={})

    return send_response(response_data={"status": "SUCCESS", "data": vehicles})


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
