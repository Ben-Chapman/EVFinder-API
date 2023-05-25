from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

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

    zip_code = common_params.zip
    model = common_params.model
    radius = common_params.radius

    # Usually a request to the Ford API is made with the requesting
    # user agent. The Ford API is behind Akamai, who treats a 'forged' UA as a
    # bot and will tarpit the request. So just letting this httpx UA be used.
    headers = {
        "Referer": f"https://shop.ford.com/inventory/{model}/",
    }

    common_params = {
        "make": "Ford",
        "market": "US",
        "inventoryType": "Radius",
        "maxDealerCount": "1",
        "model": model,
        "segment": "Crossover",
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

    # Retrieve the dealer slug, which is needed for the inventory API call
    slug = await get_dealer_slug(headers, common_params)
    if "ERROR" in slug:
        error_message = (
            "An error occurred with the Ford API. "
            "Try adjusting your search parameters."
        )
        return error_response(
            error_message=error_message,
            error_data="",
            status_code=slug.split(":")[1],
        )

    if slug:
        # Retrieve the initial batch of 12 vehicles
        inventory_params = {
            **common_params,
            "dealerSlug": slug,
            "Radius": radius,
            "Order": "Distance",
        }

    inv = await get_ford_inventory(headers=headers, params=inventory_params)
    # Add the dealer_slug to the response, the frontend will need this for future
    # API calls
    inv["dealerSlug"] = slug
    try:
        inv["data"]["filterResults"]
    except TypeError:
        return error_response(
            error_message=f"An error occurred with the Ford API: {inv['errorMessage']}",
            error_data=inv["errorMessage"],
        )

    try:
        total_count = inv["data"]["filterResults"]["ExactMatch"]["totalCount"]
        # The Ford inventory API pages 12 vehicles at a time, and their API does not
        # accept a random high value for endIndex, nor does it seem to allow for
        # paging by greater than 100 vehicles at a time. So making N number of API
        # requests, incremented by amount_to_index_by each loop.

        begin_index = 12
        end_index = 0
        amount_to_index_by = 90

        if total_count > begin_index:  # If we have more than 12 vehicles in inventory
            vehicles = []
            dealers = []
            while (
                begin_index < total_count
            ):  # Loop until we've paged through all vehicles
                # The Ford API seems to be picky about the value of end_index, so
                # if a run of this loop would calculate the end_index to be greater
                # than the total amount of inventory, just use the total_count as the
                # end_index value
                if (end_index + amount_to_index_by) > total_count:
                    end_index = total_count
                else:
                    end_index = begin_index + amount_to_index_by

                remainder_inventory_params = {
                    **inventory_params,
                    "beginIndex": begin_index,
                    "endIndex": end_index,
                }
                remainder = await get_ford_inventory(
                    headers=headers, params=remainder_inventory_params
                )

                # A ton of data is returned from the Ford API, most of it unused by
                # the site. Just storing what's actually used to dramatically reduce
                # the response size back to the front end.
                vehicles.append(
                    remainder["data"]["filterResults"]["ExactMatch"]["vehicles"]
                )
                dealers.append(
                    remainder["data"]["filterSet"]["filterGroupsMap"]["Dealer"][0][
                        "filterItemsMetadata"
                    ]["filterItems"]
                )

                begin_index += amount_to_index_by

            # Return the inventory results + the data from the remainder api calls
            inv["rdata"] = {"vehicles": vehicles, "dealers": dealers}

            # return send_response(response_data=inv, cache_control_age=3600)
    except TypeError as e:
        print(f"No pagination for Inventory call: {e}")

    return send_response(response_data=inv, cache_control_age=3600)


@router.get("/vin/ford")
async def get_ford_vin_detail(req: Request) -> dict:
    vin = req.query_params.get("vin")
    zip_code = req.query_params.get("zip")
    year = req.query_params.get("year")
    dealer_slug = req.query_params.get("dealerSlug")
    model_slug = req.query_params.get("modelSlug")
    pa_code = req.query_params.get("paCode")

    headers = {
        "Referer": (
            f"https://shop.ford.com/inventory/mach-e/results?"
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
        "segment": "Crossover",
        "zipcode": zip_code,
    }

    async with AsyncHTTPClient(
        base_url=ford_base_url,
        timeout_value=30,
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
async def get_dealer_slug(headers, params):
    """Helper function which obtains a dealer slug from the Ford API. This dealer slug
    is needed for all future inventory/VIN API requests
    """
    async with AsyncHTTPClient(
        base_url=ford_base_url,
        timeout_value=30,
        verify=verify_ssl,
    ) as http:
        dealers = await http.get(
            uri="/aemservices/cache/inventory/dealer/dealers",
            headers=headers,
            params=params,
        )

    if dealers.status_code >= 400:
        return f"ERROR: {dealers.status_code}"
    else:
        dealers = dealers.json()
        if (
            dealers["status"].lower() == "success"
            and len(dealers["data"]["Response"]) > 0
        ):
            return dealers["data"]["firstFDDealerSlug"]


async def get_ford_inventory(headers, params):
    """Main Ford API function which obtains inventory data for a given vehicle."""
    async with AsyncHTTPClient(
        base_url=ford_base_url, timeout_value=30, verify=verify_ssl
    ) as http:
        inventory = await http.get(
            uri="/aemservices/cache/inventory/dealer-lot",
            headers=headers,
            params=params,
        )

    return inventory.json()
