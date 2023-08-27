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

import copy
from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = False
volvo_base_url = "https://graph.volvocars.com"


@router.get("/inventory/volvo")
async def get_volvo_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    geo = req.query_params.get("geo")
    # year = common_params.year
    # model = common_params.model
    radius = common_params.radius
    ua = req.headers.get("User-Agent")

    try:
        # Make a call to get dealer information for this inventory request. This information
        # will be combined with the inventory results and returned to the front end.
        dealer_data = await get_volvo_dealers(
            user_agent=ua, geo_coordinates=geo, radius=radius
        )

        # Generate a list of dealer IDs from the dealer data. These dealer IDs need to
        # be included with the Volvo inventory API call
        dealer_ids = [
            i["partnerId"] for i in dealer_data if i["distanceFromPoint"] <= radius
        ]
    except RuntimeError:
        return error_response(
            error_message="Volvo dealer information could not be found for this request."
        )
    headers = {
        "User-Agent": ua,
        "Referer": "https://www.volvocars.com/",
        "apollographql-client-name": "cle",
    }

    # Setup the HTTPX client to be used for the many API calls throughout this router
    http = AsyncHTTPClient(
        base_url=volvo_base_url, timeout_value=30.0, verify=verify_ssl
    )

    start_value = 0  # Starting index for inventory results
    take_value = 100  # Number of vehicles to retrieve
    inventory_post_data = {
        "operationName": "CarSelectorListingCars",
        "variables": {
            "filter": {
                "skip": start_value,
                # "excludeDuplicates": False,
                "take": take_value,
                "filter": {
                    "value": {
                        "dealerId": {"value": [{"value": i} for i in dealer_ids]},
                        "available": {"value": [{"value": True}]},
                        # "commonSalesType": {
                        #     "value": [
                        #         {"value": "28A"},
                        #         {"value": "30A"},
                        #         {"value": "30C"},
                        #     ]
                        # },
                        # "orderBrandStatusPoint": {
                        #     "value": [{"value": {"min": 11200, "max": 16500}}]
                        # },
                        "engineType": {"value": [{"value": "BEV"}]},
                    }
                },
                "sort": [{"field": "orderDeliveryDate", "desc": False}],
            },
            "locale": "en-US",
        },
        "query": "query CarSelectorListingCars($filter: CLESearchFilterWithDistributionChannel!, $locale: String!) { stockCars(filter: $filter) { metadata { returnedHits totalHits __typename } aggregations { name values { count value value2 aggregation { name values { count value value2 __typename } __typename } __typename } __typename } hits { vehicle { dealer { id __typename } id vin modelYear specification { pno { pno12 pno34PlusOptions __typename } model(locale: $locale) { displayName { value __typename } __typename } driveline { content(locale: $locale) { driveType { value __typename } __typename } __typename } trim(locale: $locale) { displayName { value __typename } __typename } engine { content(locale: $locale) { engineCode fuelType { formatted value __typename } displayName { value __typename } engineType { formatted value __typename } __typename } __typename } visualizations(marketOrLocale: $locale) { icons { color { code default { key transparentUrl __typename } __typename } __typename } views { interior { studio { seatFabric { sizes { small { key transparentUrl __typename } __typename } __typename } __typename } __typename } exterior { studio { threeQuartersFrontLeft { key sizes { large { key transparentUrl __typename } medium { key transparentUrl __typename } small { key transparentUrl __typename } default { key transparentUrl __typename } __typename } __typename } __typename } __typename } __typename } __typename } __typename } configuration { wheels { description { language text __typename } __typename } exteriorTheme { description { language text __typename } __typename } color { code hex description { language text __typename } groupCode groupDescription { language text __typename } __typename } upholstery { code description { language text __typename } groupCode groupDescription { language text __typename } __typename } __typename } price { msrpAmount __typename } order { commonOrderNumber commonSalesType brandStatusPoint deliveryDate estimatedCustomerDeliveryLeadTimeUnit estimatedCustomerDeliveryLeadTime __typename } __typename } __typename } __typename }}",  # noqa: B950
    }

    # Make the initial inventory API call. Depending on the amount of available inventory
    # multiple future API calls may need to be made.
    inv = await http.post(
        uri="/graphql",
        headers=headers,
        post_data=inventory_post_data,
    )

    try:
        data = inv.json()
    except ValueError:
        return error_response(
            error_message="An error occurred obtaining vehicle inventory for this search.",
            error_data=inv.text,
        )

    total_count = data["data"]["stockCars"]["metadata"]["totalHits"]
    total_inventory = []
    if total_count > take_value:
        print(f"Making more api calls: {total_count}")
        # We have more inventory to fetch
        start_value = take_value
        step = take_value

        urls_to_fetch = []
        for i in range(start_value, total_count, step):
            start_value = i + 1

            # Ensure we don't request more than the total_count of pages returned for this
            # inventory request
            if i + step > total_count:
                inventory_post_data["variables"]["filter"]["take"] = (
                    total_count - start_value
                )

            inventory_post_data["variables"]["filter"]["skip"] = start_value

            # Create a list of requests which will be passed to httpx
            urls_to_fetch.append(
                ["/graphql", headers, copy.deepcopy(inventory_post_data)]
            )

        remainder = await http.post(uri=urls_to_fetch)
        await http.close()

    try:
        total_inventory.append(data["data"]["stockCars"]["hits"])
        if type(remainder) == list:
            [
                total_inventory.append(i.json()["data"]["stockCars"]["hits"])
                for i in remainder
            ]
        else:
            total_inventory.append(remainder.json()["data"]["stockCars"]["hits"])
    except Exception:
        pass

    return send_response(
        response_data=total_inventory,
        cache_control_age=3600,
    )


@router.get("/vin/volvo")
async def get_volvo_vin_detail(req: Request) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.volvousa.com/inventory/",
    }

    vin = req.query_params.get("vin")

    vin_post_data = (
        {
            "query": "query inventory { getInventoryByIdentifier("
            + f'identifier: "{vin}")'
            + " { result { code id dealerId dealerLocation vin totalMsrp name powertrain fuelType marketingText orderStatus technicalText acceleration horsepower milesPerGallon milesPerGallonEqv modelYear productionNumber sold hybridFlag sportsFlag vehicleDetailsPage destinationAndHandling qualifiedModelCode series { code name } bodyStyle { code name } engineDriveType { code name } options { name code optionPackageCodeKey price wholesalePrice optionType optionAttribute isPaint isUpholstery isPackage isTrim isAccessory isWheel isStandard isLine isTop isUni isMetallic isIndividual isMarketing } vehicleDetailsPage vehicleProcessingCenter isAtPmaDealer } dealerInfo { centerID newVehicleSales { dealerName distance longitude locationID dealerURL phoneNumber address { lineOne lineTwo city state zipcode } } } } }"  # noqa: B950
        },
    )

    async with AsyncHTTPClient(
        base_url=volvo_base_url,
        timeout_value=30.0,
        verify=verify_ssl,
    ) as http:
        v = await http.post(uri="/", headers=headers, post_data=vin_post_data)
        data = v.json()

    if len(data[0]["data"]["getInventoryByIdentifier"]["result"]) > 0:
        return send_response(response_data=data[0], cache_control_age=3600)
    else:
        error_message = "An error occurred with the  Volvo API"
        return error_response(error_message=error_message, error_data=data)


async def get_volvo_dealers(
    user_agent: str, geo_coordinates: str, radius: int
) -> list | dict:
    """Retrieve a list of dealers for a given latitude and longitude

    Args:
        user_agent (str): A user-agent HTTP header to include with this request.
        geo_coordinates (str): A string containing latitude_longitude to include with
        this request.

    Returns:
        list | dict: A list containing the unique dealer IDs returned from this
        request if successful. If the response back from the Volvo API does not include
        the required data, a meaningful HTTPException error response is returned to the
        caller.
    """

    lat, lon = geo_coordinates.split("_")  # lat and lon is provided as lat_lon
    volvo_dealer_base_url = "https://www.volvocars.com"
    headers = {
        "User-Agent": user_agent,
        "Referer": "https://www.volvocars.com/us/inventory/car-locator",
    }
    params = {
        "latitude": lat,
        "longitude": lon,
        "market": "us",
        "offset": 0,
        "capabilities": "new_car_sales",
        "distanceUnit": "Miles",
    }
    async with AsyncHTTPClient(
        base_url=volvo_dealer_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        g = await http.get(
            uri="/api/inventory/retailers/locations",
            headers=headers,
            params=params,
        )

    try:
        dealer_data = g.json()["data"]
        return dealer_data
    except KeyError:
        raise RuntimeError
