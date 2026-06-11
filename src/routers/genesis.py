# Copyright 2023 Ben Chapman
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
genesis_base_url = "https://www.genesis.com"

genesis_search_uri = "/bin/api/v2/inventory/search"

# How many dealers to search across. The v2 API honors the radius filter, so this
# only caps the number of dealers considered, not the search distance.
genesis_max_dealers = 100

# Each v2 vehicle record carries fields the inventory UI never renders. Project each
# record down to just the fields the frontend maps onto its table columns (keeping the
# OEM field names; the frontend does the OEM -> column-key mapping).
genesis_vehicle_fields = (
    "VIN",
    "ModelYear",
    "Model",
    "TrimDesc",
    "SortablePrice",
    "FormattedPrice",
    "ExtColorDesc",
    "IntColor",
    "Drivetrain",
    "PlannedDeliveryDate",
    "DlrName",
    "Distance",
)


def slim_vehicle(vehicle: dict) -> dict:
    """Project a v2 vehicle record down to the fields the inventory UI renders.

    Args:
        vehicle: A single vehicle record from the v2 search response.

    Returns:
        A dict containing only the fields in genesis_vehicle_fields that are present.
    """
    return {key: vehicle[key] for key in genesis_vehicle_fields if key in vehicle}


@router.get("/inventory/genesis")
async def get_genesis_inventory(
    req: Request,
    common_params: CommonInventoryQueryParams = Depends(),
) -> dict:
    """Makes a request to the Genesis v2 inventory API and returns the inventory results
    for a given vehicle model and zip code.

    The v2 API does not accept a model year; it returns current inventory filtered by
    zip code and radius. The EV Finder frontend filters the results by the model year
    selected for the search.

    Args:
        req (Request): The HTTP request from the EV Finder application.
        common_params (CommonInventoryQueryParams, optional): The EV Finder query params.
        Typically zip, year, model and radius. Defaults to Depends().

    Returns:
        dict: A JSON object containing the inventory results for the given search.
    """

    # The v2 search API identifies models by a lowercase slug (e.g. "gv60",
    # "electrified-g80"), while the UI sends them upper-cased.
    params = {
        "model": common_params.model.lower(),
        "zip": common_params.zip,
        "radius": common_params.radius,
        "maxdealers": genesis_max_dealers,
    }

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": f"{genesis_base_url}/us/en/new/inventory.html",
    }

    async with AsyncHTTPClient(
        base_url=genesis_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        inv = await http.get(
            uri=genesis_search_uri,
            headers=headers,
            params=params,
        )

    try:
        payload = inv.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Genesis API: {inv.text}"
        )

    result = payload.get("result") or {}

    # A non-SUCCESS result status indicates the API rejected the search rather than
    # simply returning no inventory.
    if result.get("status") not in (None, "SUCCESS"):
        return error_response(
            error_message="Received invalid data from the Genesis API",
            error_data=payload,
            status_code=400,
        )

    vehicles = [slim_vehicle(v) for v in result.get("vehicles") or []]

    # If no vehicles were returned, there is no inventory. Return an empty dict response
    # which the UI uses to display the no inventory message.
    if not vehicles:
        return send_response(response_data={})

    return send_response(response_data={"status": "SUCCESS", "data": vehicles})


@router.get("/vin/genesis")
async def get_genesis_vin_detail(req: Request) -> dict:
    vin_params = {
        "zip": req.query_params.get("zip"),
        "vin": req.query_params.get("vin"),
    }

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": f"{genesis_base_url}/us/en/new/inventory.html?vin={vin_params['vin']}",
    }

    async with AsyncHTTPClient(
        base_url=genesis_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        v = await http.get(
            uri=("/bin/api/v1/vehicledetails.json"),
            headers=headers,
            params=vin_params,
        )

        vin_data = v.json()

        if len(vin_data) > 0:
            return send_response(
                response_data=vin_data,
            )
        else:
            error_message = (
                "An error occurred obtaining VIN information for this vehicle."
            )
            return error_response(error_message=error_message, error_data=vin_data)
