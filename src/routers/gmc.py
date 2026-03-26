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
from src.routers.logger import send_error_to_gcp

router = APIRouter(prefix="/api")
verify_ssl = True
gmc_base_url = "https://www.gmc.com/gmc/shopping/api"
generic_error_message = "An error occurred obtaining GMC inventory results."

# Known trim names for all GMC EVs. Any trim name returned by the inventory API
# that is not in this set will trigger a GCP alert so the map can be kept current.
_KNOWN_GMC_TRIMS: frozenset[str] = frozenset(
    {
        # Sierra EV
        "Elevation Standard Range",
        "Elevation Extended Range",
        "Denali Standard Range",
        "Extended Range Denali",
        "Max Range Denali",
        "AT4 Extended Range",
        "AT4 Max Range",
        "Denali Max Range",
        # HUMMER EV Pickup
        "2X",
        "3X",
    }
)


def _log_unknown_trims(hits: list[dict], request: Request) -> None:
    """Log a GCP alert for each vehicle trim not present in _KNOWN_GMC_TRIMS.

    Args:
        hits: Raw vehicle records from the GMC inventory API.
        request: The originating FastAPI request, used for alert context.
    """
    seen: set[str] = set()
    for vehicle in hits:
        trim = (vehicle.get("variant") or {}).get("name")
        if trim and trim not in _KNOWN_GMC_TRIMS and trim not in seen:
            seen.add(trim)
            send_error_to_gcp(
                f"GMC: unrecognized trim '{trim}' — add to _KNOWN_GMC_TRIMS "
                "and gmcInteriorByTrim in gmcMappings.js.",
                http_context={
                    "method": "GET",
                    "url": str(request.url),
                    "user_agent": request.headers.get("User-Agent", ""),
                    "status_code": 200,
                },
            )


@router.get("/inventory/gmc")
async def get_gmc_inventory(
    req: Request, req_params: CommonInventoryQueryParams = Depends()
) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.gmc.com/",
        "client": "T1_VSR",
        "tenantId": "0",
        "dealerId": "0",
        "oemId": "GM",
        "programId": "GMC",
    }

    post_data = {
        "filters": {
            "geo": {
                "zipCode": req_params.zip,
                "radius": req_params.radius,
            },
            "model": {"values": [req_params.model.lower()]},
        },
        "sort": {"name": "distance", "order": "ASC"},
        "paymentTypes": ["CASH"],
        "pagination": {"size": 100},
    }

    inventory_uri = "/aec-cp-discovery-api/p/v1/vehicles/search"
    facets_uri = "/aec-cp-discovery-api/p/v1/vehicles/facets"

    async with AsyncHTTPClient(
        base_url=gmc_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        i = await http.post(uri=inventory_uri, headers=headers, post_data=post_data)
        f = await http.post(uri=facets_uri, headers=headers, post_data={})

        try:
            inventory = i.json()
        except ValueError:
            return error_response(error_message=generic_error_message)

        try:
            all_hits = list(inventory["data"]["hits"])
        except KeyError:
            try:
                inventory["errorDetails"]["key"]
                return send_response(response_data={})
            except Exception:
                return error_response(
                    error_message=generic_error_message,
                    error_data=inventory,
                    status_code=500,
                )

        # The GMC API caps page size at 20. Fetch remaining pages via cursor token
        # until all vehicles matching the search have been collected.
        while next_token := (
            inventory.get("data", {}).get("pagination", {}).get("nextPageToken")
        ):
            page_post_data = {
                **post_data,
                "pagination": {
                    **post_data["pagination"],
                    "nextPageToken": next_token,
                },
            }
            page = await http.post(
                uri=inventory_uri, headers=headers, post_data=page_post_data
            )
            try:
                inventory = page.json()
                all_hits.extend(inventory.get("data", {}).get("hits", []))
            except ValueError:
                break

    inventory["data"]["hits"] = all_hits

    try:
        inventory["facets"] = f.json()
    except (ValueError, AttributeError):
        pass

    _log_unknown_trims(all_hits, req)

    return send_response(response_data=inventory, cache_control_age=3600)


@router.get("/vin/gmc")
async def get_gmc_vin_detail(req: Request) -> dict:
    # TODO: Update this endpoint to the new GMC API once the VIN detail endpoint is identified
    _vin_base_url = "https://cws.gm.com"
    async with AsyncHTTPClient(
        base_url=_vin_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        params = {
            "vin": req.query_params.get("vin"),
            "postalCode": req.query_params.get("zip"),
            "customerType": "GC",
            "requesterType": "TIER_1",
            "locale": "en_US",
        }
        headers = {
            "User-Agent": req.headers.get("User-Agent"),
            "referer": _vin_base_url,
        }

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
