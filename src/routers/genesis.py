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

import datetime

from fastapi import APIRouter, Depends, Request
from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.http import AsyncHTTPClient
from src.libs.responses import error_response, send_response

router = APIRouter(prefix="/api")
verify_ssl = True
genesis_base_url = "https://www.genesis.com"


@router.get("/inventory/genesis")
async def get_genesis_inventory(
    req: Request,
    common_params: CommonInventoryQueryParams = Depends(),
) -> dict:
    """Makes a request to the Genesis Inventory API and returns a JSON object containing
    the inventory results for a given vehicle model and zip code.

    The Genesis API does not accept a search radius nor a model year, rather a maxdealers
    URI path segment. The EV Finder frontend deals with filtering the results to display
    the relevant information for the search performed.

    Args:
        req (Request): The HTTP request from the EV Finder application.
        common_params (CommonInventoryQueryParams, optional): The EV Finder query params.
        Typically zip, year, model and radius. Defaults to Depends().

    Returns:
        dict: A JSON object containing the inventory results for the given search.
    """

    zipcode = common_params.zip
    modelname = common_params.model
    maxdealers = 50
    todays_date = datetime.datetime.now().strftime("%Y-%m-%d")

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": f"{genesis_base_url}/us/en/new/inventory.html",
    }

    async with AsyncHTTPClient(
        base_url=genesis_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        inv = await http.get(
            uri=(
                f"/bin/api/v1/inventory.json/{modelname}/{zipcode}/{maxdealers}/{todays_date}"
            ),
            headers=headers,
        )

        inventory_data = inv.json()

        if len(inventory_data) > 0:
            return send_response(
                response_data=inventory_data,
            )
        else:
            error_message = (
                "An error occurred obtaining vehicle inventory for this search."
            )
            return error_response(
                error_message=error_message, error_data=inventory_data
            )


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
