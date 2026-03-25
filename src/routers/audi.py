# Copyright 2023 - 2025 Ben Chapman
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
from src.libs.http import AsyncHTTPClient
from src.libs.responses import error_response, send_response

router = APIRouter(prefix="/api")
verify_ssl = False  # onegraph.audi.com uses a self-signed certificate chain
audi_base_url = "https://onegraph.audi.com"

# GraphQL query string for the StockCarSearch operation
_STOCK_CAR_SEARCH_QUERY = (
    "query StockCarSearch($stockIdentifier: StockIdentifierInput!, "
    "$searchParameter: StockCarSearchParameterInput, "
    "$groupIds: [String!], $imageIds: [String!]) {\n"
    "  stockCarSearch(\n"
    "    stockIdentifier: $stockIdentifier\n"
    "    searchParameter: $searchParameter\n"
    "  ) {\n"
    "    resultNumber\n"
    "    search {\n"
    "      criteria {\n"
    "        id\n"
    "        possibleItems {\n"
    "          id\n"
    "          number\n"
    "          __typename\n"
    "        }\n"
    "        selectedItems {\n"
    "          id\n"
    "          number\n"
    "          __typename\n"
    "        }\n"
    "        __typename\n"
    "      }\n"
    "      __typename\n"
    "    }\n"
    "    results {\n"
    "      sort {\n"
    "        id\n"
    "        direction\n"
    "        __typename\n"
    "      }\n"
    "      paging {\n"
    "        limit\n"
    "        offset\n"
    "        __typename\n"
    "      }\n"
    "      cars {\n"
    "        geoDistance {\n"
    "          unitText\n"
    "          value {\n"
    "            formatted\n"
    "            number\n"
    "            __typename\n"
    "          }\n"
    "          __typename\n"
    "        }\n"
    "        stockCar {\n"
    "          code {\n"
    "            id\n"
    "            __typename\n"
    "          }\n"
    "          id\n"
    "          vin\n"
    "          weblink\n"
    "          titleText\n"
    "          model {\n"
    "            name\n"
    "            salesModelyear\n"
    "            id {\n"
    "              code\n"
    "              __typename\n"
    "            }\n"
    "            __typename\n"
    "          }\n"
    "          modelInfo {\n"
    "            genericModel {\n"
    "              code\n"
    "              text\n"
    "              __typename\n"
    "            }\n"
    "            modelyear\n"
    "            __typename\n"
    "          }\n"
    "          dealer {\n"
    "            id\n"
    "            name\n"
    "            region\n"
    "            __typename\n"
    "          }\n"
    "          carPrices {\n"
    "            label\n"
    "            price {\n"
    "              value\n"
    "              valueAsText\n"
    "              formattedValue\n"
    "              __typename\n"
    "            }\n"
    "            type\n"
    "            __typename\n"
    "          }\n"
    "          salesInfo {\n"
    "            availableFromDateInfo {\n"
    "              type\n"
    "              value\n"
    "              __typename\n"
    "            }\n"
    "            orderStatusText\n"
    "            saleOrderTypeText\n"
    "            __typename\n"
    "          }\n"
    "          qualityLabel {\n"
    "            label\n"
    "            __typename\n"
    "          }\n"
    "          subtitleText\n"
    "          cartypeText\n"
    "          preUse {\n"
    "            code\n"
    "            text\n"
    "            __typename\n"
    "          }\n"
    "          commissionNumber\n"
    "          images(groupIds: $groupIds, imageIds: $imageIds) {\n"
    "            url\n"
    "            type\n"
    "            mimeType\n"
    "            id {\n"
    "              group\n"
    "              image\n"
    "              __typename\n"
    "            }\n"
    "            __typename\n"
    "          }\n"
    "          colorInfo {\n"
    "            exteriorColor {\n"
    "              colorInfo {\n"
    "                text\n"
    "                __typename\n"
    "              }\n"
    "              baseColorInfo {\n"
    "                code\n"
    "                text\n"
    "                __typename\n"
    "              }\n"
    "              __typename\n"
    "            }\n"
    "            interiorColor {\n"
    "              colorInfo {\n"
    "                text\n"
    "                __typename\n"
    "              }\n"
    "              baseColorInfo {\n"
    "                code\n"
    "                text\n"
    "                __typename\n"
    "              }\n"
    "              __typename\n"
    "            }\n"
    "            __typename\n"
    "          }\n"
    "          driveText\n"
    "          dynamicAttributes {\n"
    "            id\n"
    "            value\n"
    "            __typename\n"
    "          }\n"
    "          engineInfo {\n"
    "            fuel {\n"
    "              code\n"
    "              text\n"
    "              __typename\n"
    "            }\n"
    "            __typename\n"
    "          }\n"
    "          carline {\n"
    "            id\n"
    "            name\n"
    "            __typename\n"
    "          }\n"
    "          gearText\n"
    "          metaData {\n"
    "            statImport\n"
    "            __typename\n"
    "          }\n"
    "          mileage {\n"
    "            unitText\n"
    "            value {\n"
    "              formatted\n"
    "              number\n"
    "              __typename\n"
    "            }\n"
    "            __typename\n"
    "          }\n"
    "          __typename\n"
    "        }\n"
    "        __typename\n"
    "      }\n"
    "      __typename\n"
    "    }\n"
    "    __typename\n"
    "  }\n"
    "}"
)


@router.get("/inventory/audi")
async def get_audi_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    # geo is provided by the frontend as "lat_lng" (e.g. "34.06965_-118.396306")
    geo = req.query_params.get("geo")
    lat, lng = geo.split("_")
    model = common_params.model
    radius = common_params.radius
    # TODO: Identify the salesModelYear criteria ID on the new onegraph API and add
    # year filtering to the criteria list below.
    year = common_params.year  # noqa: F841

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.audiusa.com/",
        "apollographql-client-name": "audiusa",
        "apollographql-client-version": "1.0.0",
    }

    amount_to_page_by = 12
    offset = 0

    inventory_post_data = {
        "operationName": "StockCarSearch",
        "variables": {
            "stockIdentifier": {
                "marketIdentifier": {
                    "brand": "A",
                    "country": "us",
                    "language": "en",
                },
                "stockCarsType": "NEW",
            },
            "searchParameter": {
                "geo": {
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "maxDistance": radius,
                },
                "paging": {
                    "limit": amount_to_page_by,
                    "offset": offset,
                },
                "sort": {
                    "id": "DATE_PREDATEEND",
                    "direction": "ASC",
                },
                "criteria": [
                    {"id": "model-range", "items": [model]},
                    {"id": "stat-import", "items": ["AGC_USA_JDP"]},
                    {"id": "sold-order", "items": ["no"]},
                ],
            },
            "groupIds": ["renderImagesPNG", "dealerImages"],
            "imageIds": ["sc5c01", "sc4c03", "sc4c11", "1", "2", "3"],
        },
        "query": _STOCK_CAR_SEARCH_QUERY,
    }

    # Setup the HTTPX client to be used for the many API calls throughout this router
    http = AsyncHTTPClient(
        base_url=audi_base_url, timeout_value=30.0, verify=verify_ssl
    )

    inv = await http.post(
        uri="/graphql", headers=headers, post_data=inventory_post_data
    )
    try:
        inventory_data = inv.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Audi inventory service: {inv.text}"
        )

    try:
        # If the inventory request was successful, even if 0 vehicles are returned
        # the response will have the ['data'] dict, so validating that
        inventory_data["data"]["stockCarSearch"]
    except KeyError:
        error_message = "An error occurred with the Audi inventory service"
        return error_response(error_message=error_message, error_data=inventory_data)

    total_vehicle_count = inventory_data["data"]["stockCarSearch"]["resultNumber"]

    if total_vehicle_count <= amount_to_page_by:
        return send_response(response_data=inventory_data)
    else:
        begin_index = amount_to_page_by
        end_index = total_vehicle_count
        step = amount_to_page_by

        urls_to_fetch = []

        for i in range(begin_index, end_index, step):
            # Make a deep copy of the inventory_post_data dict to allow for value updates
            # in this loop
            tmp = copy.deepcopy(inventory_post_data)
            tmp["variables"]["searchParameter"]["paging"]["offset"] = i

            # Add the post data to our URL list
            urls_to_fetch.append(["/graphql", headers, tmp])

        remainder = await http.post(uri=urls_to_fetch)

        # HTTP requests to the Audi API are complete, close the connection.
        await http.close()

        if type(remainder) is not list:
            remainder = [remainder]

        for api_result in remainder:
            try:
                result = api_result.json()
                remainder_cars = result["data"]["stockCarSearch"]["results"]["cars"]
                inventory_data["data"]["stockCarSearch"]["results"]["cars"].extend(
                    remainder_cars
                )
            except AttributeError:
                inv["apiErrorResponse"] = True

        return send_response(response_data=inventory_data, cache_control_age=3600)


@router.get("/vin/audi")
async def get_audi_vin_detail(req: Request) -> dict:
    # vehicleId holds the VIN string (e.g. "WAUJ8BFW5S7901084")
    vin = req.query_params.get("vehicleId")

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.audiusa.com/",
        "apollographql-client-name": "audiusa",
        "apollographql-client-version": "1.0.0",
    }

    vin_post_data = {
        "operationName": "StockCarSearch",
        "variables": {
            "stockIdentifier": {
                "stockCarsType": "NEW",
                "marketIdentifier": {
                    "language": "en",
                    "country": "us",
                    "brand": "A",
                },
            },
            "searchParameter": {
                "paging": {"limit": 2, "offset": 0},
                "criteria": [
                    {"id": "stat-import", "items": ["AGC_USA_JDP"]},
                    {"id": "t_vin", "items": [vin]},
                ],
            },
            "groupIds": ["renderImagesPNG"],
            "imageIds": ["sc4c14", "sc4c03"],
        },
        "query": "query StockCarSearch($stockIdentifier: StockIdentifierInput!, $searchParameter: StockCarSearchParameterInput, $groupIds: [String!], $imageIds: [String!]) {\n  stockCarSearch(\n    stockIdentifier: $stockIdentifier\n    searchParameter: $searchParameter\n  ) {\n    resultNumber\n    results {\n      cars {\n        stockCar {\n          ...StockCarFragment\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment StockCarFragment on StockCar {\n  id\n  vin\n  commissionNumber\n  titleText\n  subtitleText\n  cartypeText\n  model {\n    id {\n      year\n      code\n      __typename\n    }\n    name\n    __typename\n  }\n  modelInfo {\n    modelyear\n    genericModel {\n      code\n      text\n      __typename\n    }\n    __typename\n  }\n  dealer {\n    id\n    name\n    __typename\n  }\n  preUse {\n    text\n    __typename\n  }\n  descriptionByDealer\n  colorInfo {\n    exteriorColor {\n      label\n      colorInfo {\n        text\n        code\n        __typename\n      }\n      baseColorInfo {\n        text\n        code\n        __typename\n      }\n      imageUrl\n      __typename\n    }\n    interiorColor {\n      label\n      colorInfo {\n        text\n        code\n        __typename\n      }\n      baseColorInfo {\n        text\n        code\n        __typename\n      }\n      imageUrl\n      __typename\n    }\n    __typename\n  }\n  images(groupIds: $groupIds, imageIds: $imageIds) {\n    id {\n      group\n      image\n      __typename\n    }\n    url\n    __typename\n  }\n  salesInfo {\n    availableFromDateInfo {\n      value\n      __typename\n    }\n    __typename\n  }\n  dynamicAttributes {\n    id\n    value\n    __typename\n  }\n  manufacturerSpecificItems {\n    ... on StockCarManufacturerAudi {\n      cdbItems {\n        id\n        value\n        textInfos {\n          id\n          value\n          __typename\n        }\n        __typename\n      }\n      cdbCategories {\n        id\n        label\n        categories {\n          id\n          label\n          features {\n            text\n            featureType\n            prNumber {\n              class\n              __typename\n            }\n            textInfos {\n              name\n              details\n              benefits\n              __typename\n            }\n            imageResources {\n              id\n              value\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  techDataGroups {\n    id\n    label\n    techDataList {\n      id\n      text\n      label\n      __typename\n    }\n    __typename\n  }\n  engineInfo {\n    fuel {\n      text\n      __typename\n    }\n    __typename\n  }\n  __typename\n}",  # noqa: E501
    }

    async with AsyncHTTPClient(
        base_url=audi_base_url,
        timeout_value=30.0,
        verify=verify_ssl,
    ) as http:
        v = await http.post(uri="/graphql", headers=headers, post_data=vin_post_data)
        data = v.json()

    try:
        data["data"]["stockCarSearch"]
        return send_response(response_data=data, cache_control_age=3600)
    except KeyError:
        error_message = "An error occurred with the Audi inventory service"
        return error_response(error_message=error_message, error_data=data)
