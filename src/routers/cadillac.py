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

cadillac_base_url = "https://www.cadillac.com/cadillac/shopping/api"
inventory_uri = "/aec-cp-discovery-api/p/v1/vehicles/search"
vin_uri = "/aec-cp-ims-apigateway/p/v1/vehicles/detail"
page_size = 20

generic_error_message = "An error occurred obtaining Cadillac inventory results."


@router.get("/inventory/cadillac")
async def get_cadillac_inventory(
    req: Request, req_params: CommonInventoryQueryParams = Depends()
) -> dict:
    zip_code = str(req_params.zip)
    year = str(req_params.year)
    model = req_params.model
    radius = req_params.radius

    inventory_post_data = {
        "filters": {
            "vehicleCategory": {"values": ["EV"]},
            "year": {"values": [year]},
            "model": {"values": [model]},
            "geo": {"zipCode": zip_code, "radius": radius},
        },
        "sort": {"name": "distance", "order": "ASC"},
        "paymentTypes": ["CASH"],
        "pagination": {"size": page_size},
    }
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": f"https://www.cadillac.com/shopping/inventory/search/{model}/{year}",
        "oemId": "GM",
        "programId": "CADILLAC",
        "dealerId": "0",
        "tenantId": "0",
        "client": "T1_VSR",
    }

    # Setup the HTTPX client to be used for the many API calls throughout this router
    http = AsyncHTTPClient(
        base_url=cadillac_base_url, timeout_value=30.0, verify=verify_ssl
    )

    # Some Cadillac vehicle detail is accessible through a separate API endpoint. Making
    # that call here, and will combine with the inventory results later.
    facets_post_data = {
        "filters": {
            "model": {"values": [model]},
            "geo": {"zipCode": zip_code, "radius": radius},
        }
    }
    f = await http.post(
        uri="/aec-cp-discovery-api/p/v1/vehicles/facets",
        headers=headers,
        post_data=facets_post_data,
    )
    try:
        facets = f.json()
    except ValueError:
        pass

    # Retrieve the initial batch of vehicles
    i = await http.post(
        uri=inventory_uri, headers=headers, post_data=inventory_post_data
    )
    try:
        inventory = i.json()
    except ValueError:
        return error_response(error_message=generic_error_message)

    # Ensure the response back from the API has some status, indicating a successful
    # API call
    try:
        inventory["status"]
    except KeyError:
        return error_response(
            error_message=generic_error_message,
            error_data=inventory,
            status_code=500,
        )

    # The Cadillac API returns a 404 and JSON response with a inventory.notfound key if
    # no vehicles are found. Checking for that condition and returning an empty dict
    if (
        inventory.get("errorDetails")
        and inventory["errorDetails"]["key"] == "inventory.notFound"
    ):
        return send_response(response_data={})

    inventory_result_count = inventory.get("data").get("count")

    # We have only one page of results, so just return the JSON response back to the
    # frontend.
    if inventory_result_count <= page_size:
        return send_response(response_data=inventory)
    else:
        # The Cadillac inventory API pages 20 vehicles at a time. Making N number of API
        # requests, incremented by step.
        begin_index = page_size
        step = page_size
        # nextPageToken is required to be sent with the API request to retrieve the next
        # page of vehicles
        next_page_token = inventory.get("data").get("pagination").get("nextPageToken")

        for i in range(begin_index, inventory_result_count, step):
            begin_index = i

            # Add the nextPageToken to subsequent requests
            remainder_inventory_post_data = {
                **inventory_post_data,
                "pagination": {
                    "size": page_size,
                    "nextPageToken": next_page_token,
                },
            }

            # The Cadillac API uses nextPageToken to retrieve the next page of vehicles
            # so we have to loop through the
            remainder_i = await http.post(
                uri=inventory_uri,
                headers=headers,
                post_data=remainder_inventory_post_data,
            )

            # Push this page of results into the inventory dict
            try:
                remainder = remainder_i.json()
                inventory["data"]["hits"] = (
                    inventory["data"]["hits"] + remainder["data"]["hits"]
                )
            except AttributeError:
                i["apiErrorResponse"] = True

            next_page_token = (
                remainder.get("data").get("pagination").get("nextPageToken")
            )

    await http.close()

    # Combine the facets data with the inventory data
    inventory["facets"] = facets
    return send_response(response_data=inventory, cache_control_age=3600)


@router.get("/vin/cadillac")
async def get_cadillac_vin_detail(req: Request) -> dict:
    # Make a call to the Cadillac API
    async with AsyncHTTPClient(
        base_url=cadillac_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        vin_post_data = {
            "pricing": {
                "paymentTypes": ["CASH", "FINANCE", "LEASE"],
                "finance": {"downPayment": 3500},
                "lease": {"mileage": 10000, "downPayment": 3500},
            },
            "vin": req.query_params.get("vin"),
        }

        headers = {
            "User-Agent": req.headers.get("User-Agent"),
            "Referer": f"{cadillac_base_url}/shopping/inventory/vehicle/\
                {req.query_params.get('model').upper()}/{req.query_params.get('year')}",
            "oemId": "GM",
            "programId": "CADILLAC",
            "dealerId": "0",
            "tenantId": "0",
            "client": "UI",
        }

        v = await http.post(
            uri=vin_uri,
            headers=headers,
            post_data=vin_post_data,
        )

        try:
            vin_data = v.json()
        except AttributeError:
            return error_response(error_message=v, status_code=504)
        else:
            if req.query_params.get("vin") in vin_data["data"]["id"]:
                return send_response(response_data=vin_data)
            else:
                return error_response(
                    error_message="An error occurred obtaining VIN detail for this vehicle.",
                    error_data=vin_data["errorDetails"]["errorCode"],
                    status_code=400,
                )
