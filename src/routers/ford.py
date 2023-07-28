import time

from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.http import AsyncHTTPClient
from src.libs.responses import error_response, send_response

router = APIRouter(prefix="/api")
verify_ssl = True
ford_base_url = "https://shop.ford.com"


@router.get("/inventory/ford")
async def main(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """The Ford API is ...tricky and strict with the data present in the API request.
    As such, there's lots of additional logic to deal with the various peculiarities
    of this API.
    """

    start = time.perf_counter()

    zip_code = common_params.zip
    model = common_params.model
    radius = common_params.radius

    # Setup the HTTPX client to be used for the many API calls throughout this router
    http = AsyncHTTPClient(
        base_url=ford_base_url, timeout_value=30.0, verify=verify_ssl
    )

    # Usually a request to the Ford API is made with the requesting user agent. The Ford
    # API is behind Akamai, who treats a 'forged' UA as a bot and will tarpit the request.
    # So just letting this httpx UA be used.
    headers = {
        "Referer": f"https://shop.ford.com/inventory/{model}/",
    }

    segment_type = {"mache": "Crossover", "f-150 lightning": "Truck"}

    common_params = {
        "make": "Ford",
        "market": "US",
        "inventoryType": "Radius",
        "maxDealerCount": "1",
        "model": model,
        "segment": segment_type[model],
        "zipcode": zip_code,
    }

    # Ford apparently does not support radius searches > 500 miles. For now, returning
    # an error message to users who attempt a search radius > 500  miles.
    # TODO: Deal with this in the UI, with better info messaging
    if int(radius) > 500:
        return error_response(
            error_message="Retry your request with a radius between 1 and 500 miles.",
            error_data="",
            status_code=400,
        )

    dealers_uri = "/aemservices/cache/inventory/dealer/dealers"
    inventory_uri = "/aemservices/cache/inventory/dealer-lot"

    # Retrieve the dealer slug, which is needed for the inventory API call
    dealers = await http.get(
        uri=dealers_uri,
        headers=headers,
        params=common_params,
    )
    try:
        dealers = dealers.json()
    except ValueError:
        error_response("An error occurred with the Ford API. Please try again later.")
    else:
        slug = parse_dealer_slug(dealers)

        if "ERROR" in slug:
            error_message = (
                "An error occurred with the Ford API. "
                "Try adjusting your search parameters."
            )
            return error_response(
                error_message=error_message,
                error_data="",
            )

    if slug:
        inventory_params = {
            **common_params,
            "dealerSlug": slug,
            "Radius": radius,
            "Order": "Distance",
        }
    # Retrieve the initial batch of 12 vehicles
    inv = await http.get(uri=inventory_uri, headers=headers, params=inventory_params)

    try:
        inv = inv.json()
    except ValueError:
        error_response("An error occurred with the Ford API. Please try again later.")

    # Add the dealer_slug to the response, the frontend will need this for future API calls
    inv["dealerSlug"] = slug

    try:
        inv["data"]["filterResults"]
    except TypeError:
        return error_response(
            error_message=f"An error occurred with the Ford API: {inv['errorMessage']}",
            error_data=inv["errorMessage"],
        )

    try:
        # The total number of vehicles found for the given search parameters
        total_count = inv["data"]["filterResults"]["ExactMatch"]["totalCount"]
    except TypeError as e:
        return error_response(
            error_message=f"An error occurred with the Ford API: {inv['errorMessage']}",
            error_data=e,
        )
    else:
        # The Ford inventory API pages 12 vehicles at a time, and their API does not
        # accept a random high value for endIndex, nor does it seem to allow for
        # paging by greater than 100 vehicles at a time. So making N number of API
        # requests, incremented by step.
        begin_index = 12
        end_index = 0
        step = 50

        urls_to_fetch = []
        vehicles = []
        dealers = []

        for i in range(begin_index, total_count, step):
            begin_index = i

            # Ensure we don't request more than the total_count of pages returned for this
            # inventory request
            if i + step < total_count:
                end_index = i + step
            else:
                end_index = total_count

            # Adding beginIndex and endIndex to the query params used to make subsequent
            # API requests
            remainder_inventory_params = {
                **inventory_params,
                "beginIndex": begin_index,
                "endIndex": end_index,
            }

            # Create a list of requests which will be passed to httpx
            urls_to_fetch.append(
                [
                    inventory_uri,
                    headers,
                    remainder_inventory_params,
                ]
            )

        remainder = await http.get(uri=urls_to_fetch)

        # Loop through the inventory results list
        for api_result in remainder:
            result = api_result.json()

            # A ton of data is returned from the Ford API, most of it unused by the site.
            # Just storing what's actually used to dramatically reduce the response size
            # back to the front end.
            vehicles.append(result["data"]["filterResults"]["ExactMatch"]["vehicles"])
            dealers.append(
                result["data"]["filterSet"]["filterGroupsMap"]["Dealer"][0][
                    "filterItemsMetadata"
                ]["filterItems"]
            )

        # Add the remainder API responses to the inventory dict
        inv["rdata"] = {"vehicles": vehicles, "dealers": dealers}

    end = time.perf_counter()
    print(f"\n\n-----\nTime taken: {end-start} sec")

    await http.close()
    return send_response(response_data=inv, cache_control_age=3600)


@router.get("/vin/ford")
async def get_ford_vin_detail(req: Request) -> dict:
    model = req.query_params.get("model")
    vin = req.query_params.get("vin")
    zip_code = req.query_params.get("zip")
    year = req.query_params.get("year")
    dealer_slug = req.query_params.get("dealerSlug")
    model_slug = req.query_params.get("modelSlug")
    pa_code = req.query_params.get("paCode")

    headers = {
        "Referer": (
            f"https://shop.ford.com/inventory/{model}/results?"
            f"zipcode={zip_code}&Radius=20&year={year}"
            f"&Order=Distance"
        )
    }

    vin_params = {
        "dealerSlug": dealer_slug,
        "modelSlug": model_slug,
        "vin": vin,
        "make": "Ford",
        "market": "US",
        "requestTowingData": "undefined",
        "inventoryType": "Radius",
        "ownerPACode": pa_code,
        "zipcode": zip_code,
    }

    async with AsyncHTTPClient(
        base_url=ford_base_url,
        timeout_value=30.0,
        verify=verify_ssl,
    ) as http:
        v = await http.get(
            uri="/aemservices/cache/inventory/dealer/vehicle-details",
            headers=headers,
            params=vin_params,
        )
        data = v.json()

    return send_response(response_data=data, cache_control_age=3600)


###
# Helper functions
###
def parse_dealer_slug(dealers: dict) -> str:
    """Helper function which retrieves a dealer slug from the Ford API. This dealer slug
    is needed for all future inventory/VIN API requests

    Args:
        dealers (dict): A JSON-parsed response from the Ford API containing a dealer slug.

    Returns:
        str: A string containing a Ford dealer slug.
    """
    if (
        dealers["status"].lower() == "success"
        and len(dealers["data"]["firstFDDealerSlug"]) > 0
    ):
        return dealers["data"]["firstFDDealerSlug"]
    else:
        return f"ERROR: {dealers['errorType']}"
