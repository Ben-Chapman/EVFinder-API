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
chevrolet_base_url = "https://www.chevrolet.com/chevrolet/shopping/api"
error_message = "An error occurred with the Chevrolet inventory service"


@router.get("/inventory/chevrolet")
async def get_chevrolet_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.chevrolet.com/shopping/inventory/search",
        "client": "T1_VSR",
        "tenantId": "0",
        "dealerId": "0",
        "oemId": "GM",
        "programId": "CHEVROLET",
    }

    inventory_post_data = {
        "filters": {
            "stockType": {"values": ["DealerStock"]},
            "year": {"values": [str(common_params.year)]},
            "model": {"values": [common_params.model.lower()]},
            "geo": {"zipCode": common_params.zip, "radius": common_params.radius},
        },
        "sort": {"name": "distance", "order": "ASC"},
        "paymentTypes": ["CASH"],
        "pagination": {"size": 100},
    }

    facets_post_data = {
        "filters": {
            "year": {"values": [str(common_params.year)]},
            "model": {"values": [common_params.model.lower()]},
            "geo": {"zipCode": common_params.zip, "radius": common_params.radius},
        }
    }

    async with AsyncHTTPClient(
        base_url=chevrolet_base_url,
        timeout_value=30.0,
    ) as http:
        i = await http.post(
            uri="/aec-cp-discovery-api/p/v1/vehicles/search",
            headers=headers,
            post_data=inventory_post_data,
        )
        # Some Chevrolet vehicle detail is accessible through a separate API endpoint.
        # Making that call here, and will combine with the inventory results later.
        f = await http.post(
            uri="/aec-cp-discovery-api/p/v1/vehicles/facets",
            headers=headers,
            post_data=facets_post_data,
        )
    try:
        inventory = i.json()
        facets = f.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Chevrolet inventory service: {i.text}"
        )

    # Add vehicle facets to the inventory response
    inventory["facets"] = facets

    try:
        inventory["data"]["hits"]
        return send_response(
            response_data=inventory,
            cache_control_age=3600,
        )
    except KeyError:
        try:
            inventory["errorDetails"]["key"]
            return send_response(response_data={})
        except Exception:
            return error_response(error_message=error_message, error_data=inventory)


@router.get("/vin/chevrolet")
async def get_chevrolet_vin_detail(req: Request) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "client": "UI",
        "tenantId": "0",
        "dealerId": "0",
        "oemId": "GM",
        "programId": "CHEVROLET",
    }

    vin = req.query_params.get("vin")
    vin_post_data = {"vin": vin}

    async with AsyncHTTPClient(
        base_url=chevrolet_base_url,
        timeout_value=30.0,
        verify=verify_ssl,
    ) as http:
        g = await http.post(
            uri="/aec-cp-ims-apigateway/p/v1/vehicles/detail",
            headers=headers,
            post_data=vin_post_data,
        )
        data = g.json()

    try:
        vin_data = data["data"]
        return send_response(response_data=vin_data, cache_control_age=3600)
    except KeyError:
        error_message = f"""An error occurred with the Chevrolet inventory service when
        fetching VIN details for {vin}"""

        return error_response(error_message=error_message, error_data=data["data"])
