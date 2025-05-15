# Copyright 2025 Ben Chapman
#
# This file is part of The EV Finder.
#
# The EV Finder is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# The EV Finder is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with The EV Finder.
# If not, see <https://www.gnu.org/licenses/>.


from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.http import AsyncHTTPClient
from src.libs.responses import error_response, send_response

router = APIRouter(prefix="/api")
verify_ssl = True
gmc_base_url = "https://cws.gm.com"
page_size = 96
generic_error_message = "An error occurred obtaining GMC inventory results."


@router.get("/inventory/gmc")
async def get_gmc_inventory(
    req: Request, req_params: CommonInventoryQueryParams = Depends()
) -> dict:
    params = {
        "conditions": "New",
        "makes": "GMC",
        "locale": "en_US",
        "models": req_params.model,
        "years": req_params.year,
        "radius": req_params.radius,
        "postalCode": req_params.zip,
        "pageSize": page_size,
        "sortby": "bestMatch:desc,distance:asc,netPrice:asc",
        "includeNearMatches": "true",
        "requesterType": "TIER_1_VSR",
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.gmc.com/",
    }

    inventory_uri = "/vs-cws/vehshop/v2/vehicles"

    # Setup the HTTPX client to be used for the many API calls throughout this router
    http = AsyncHTTPClient(base_url=gmc_base_url, timeout_value=30.0, verify=verify_ssl)

    # Retrieve the initial batch of {page_size} vehicles
    i = await http.get(uri=inventory_uri, headers=headers, params=params)
    try:
        inventory = i.json()
    except ValueError:
        return error_response(error_message=generic_error_message)

    # Ensure the response back from the API has some status, indicating a successful
    # API call
    try:
        inventory["resultsCount"]
    except KeyError:
        return error_response(
            error_message=generic_error_message,
            error_data=inventory,
            status_code=500,
        )

    inventory_result_count = inventory.get("resultsCount")
    # We have only one page of results, so just returning the JSON response back to the
    # frontend.
    if inventory_result_count <= page_size:
        if not inventory.get("error"):
            return send_response(response_data=inventory)
    else:
        # The GMC inventory API pages {page_size} vehicles at a time. Making N number of
        # API requests, incremented by step.
        begin_index = page_size
        end_index = 0
        step = page_size

        urls_to_fetch = []

        for i in range(begin_index, inventory_result_count, step):
            begin_index = i

            # Ensure we don't request more than the inventory_result_count of pages
            # returned for this inventory request
            if i + step < inventory_result_count:
                end_index = i + step
            else:
                end_index = inventory_result_count

            # Adding beginIndex and endIndex to the query params used to make subsequent
            # API requests
            remainder_inventory_params = {
                **params,
                "pageSize": end_index,
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

        # If we only have the initial API call and one additional API call, the response
        # back from the http helper library is a httpx.Response object. If we have multiple
        # additional API calls, the response back is a list. Catching this situation and
        # throwing that single httpx.Response object into a list for further processing.
        if type(remainder) is not list:
            remainder = [remainder]

        # Loop through the inventory results list
        for api_result in remainder:
            # When issuing concurrent API requests, some may come back with non-200
            # responses (e.g. 500) and thus no JSON response data. Catching that condition
            # and adding an item to the dict which is returned to the front end.
            try:
                result = api_result.json()
                inventory["vehicles"].append(result["vehicles"])
            except AttributeError:
                i["apiErrorResponse"] = True

    await http.close()
    return send_response(response_data=inventory, cache_control_age=3600)


@router.get("/vin/gmc")
async def get_gmc_vin_detail(req: Request) -> dict:
    # Make a call to the GMC API
    async with AsyncHTTPClient(
        base_url=gmc_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        params = {
            "vin:": req.query_params.get("vin"),
            "postalCode": req.query_params.get("postalCode"),
            "customerType": "GC",
            "requesterType": "TIER_1",
            "locale": "en_US",
        }
        headers = {"User-Agent": req.headers.get("User-Agent"), "referer": gmc_base_url}

        v = await http.get(
            uri="/vs-cws/vehshop/v2/vehicle",
            headers=headers,
            params=params,
        )

        try:
            vin_data = v.json()
        except AttributeError:
            return error_response(error_message=v, status_code=504)
        else:
            if req.query_params.get("vin") in vin_data["vin"]:
                return send_response(response_data=vin_data)
            else:
                return error_response(
                    error_message="An error occurred obtaining VIN detail for this vehicle.",
                    error_data=vin_data.split(":")[0],
                    status_code=400,
                )
