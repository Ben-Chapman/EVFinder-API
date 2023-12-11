import copy
from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = True
audi_base_url = "https://prod.aoaaudinagateway.svc.audiusa.io/graphql"


@router.get("/inventory/audi")
async def get_audi_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    geo = req.query_params.get("geo")
    year = common_params.year
    model = common_params.model
    radius = common_params.radius

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.audiusa.com/",
    }

    amount_to_page_by = 24
    offset = 0

    inventory_post_data = {
        "operationName": "getFilteredVehiclesForWormwood",
        "variables": {
            "version": "2.0.0",
            "market": ["US"],
            "lang": "en",
            "filters": (
                "available-from.immediately,"
                "available-from.soon,"
                f"geo:{geo}_{radius}_miles_defaultcity,"
                f"model-range.{model},"
                "vtp-drivetrain.electrical,"
                f"model-year.{year}"
            ),
            "sort": "byDistance:ASC",
            "limit": amount_to_page_by,
            "offset": offset,
            "preset": "foreign-brand.no,sold-order.no",
        },
        "query": "query getFilteredVehiclesForWormwood($version: String, $market: [MarketType]!, $limit: Int, $lang: String!, $filters: String, $sort: String, $offset: Int, $preset: String) { getFilteredVehiclesForWormwood( version: $version market: $market size: $limit lang: $lang filters: $filters sort: $sort from: $offset preset: $preset ) { filterResults { totalCount totalNewCarCount totalUsedCarCount available_from_soon available_from_immediately has_warranties_yes has_warranties_no __typename } vehicles { id interiorColor exteriorColor modelID modelYear modelCode modelName modelPrice modelPowerkW modelMileage audiCode stockNumber trimName kvpsSyncId dealerName dealerRegion vehicleType warrantyType modelImageFromScs isAvailableNow vin bodyType saleOrderType vehicleInventoryType vehicleOrderStatus driveType gearType distanceFromUser __typename } __typename }}",  # noqa: B950
    }
    # Setup the HTTPX client to be used for the many API calls throughout this router
    http = AsyncHTTPClient(
        base_url=audi_base_url, timeout_value=30.0, verify=verify_ssl
    )

    inv = await http.post(uri="/", headers=headers, post_data=inventory_post_data)
    try:
        inventory_data = inv.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the Audi inventory service: {inv.text}"
        )
    try:
        # If the inventory request was successful, even if 0 vehicles are returned
        # the response will have the ['data'] dict, so validating that
        inventory_data["data"]

    except KeyError:
        error_message = "An error occurred with the Audi inventory service"
        return error_response(error_message=error_message, error_data=inventory_data)

    total_vehicle_count = inventory_data["data"]["getFilteredVehiclesForWormwood"][
        "filterResults"
    ]["totalCount"]

    if total_vehicle_count <= amount_to_page_by:
        return send_response(response_data=inventory_data)
    else:
        begin_index = amount_to_page_by
        end_index = total_vehicle_count
        step = 24

        urls_to_fetch = []

        for i in range(begin_index, end_index, step):
            # Make a deep copy of the inventory_post_data dict to allow for value updates
            # in this loop
            tmp = copy.deepcopy(inventory_post_data)
            tmp["variables"]["offset"] = i

            # Add the post data to our URL list
            urls_to_fetch.append(["/", headers, tmp])

        remainder = await http.post(uri=urls_to_fetch)

        # HTTP requests to the Audi API are complete, close the connection.
        await http.close()

        if type(remainder) is not list:
            remainder = [remainder]

        for api_result in remainder:
            try:
                result = api_result.json()
                remainder_vehicles = result["data"]["getFilteredVehiclesForWormwood"][
                    "vehicles"
                ]
                inventory_data["data"]["getFilteredVehiclesForWormwood"][
                    "vehicles"
                ].extend(remainder_vehicles)
            except AttributeError:
                inv["apiErrorResponse"] = True

        return send_response(response_data=inventory_data, cache_control_age=3600)


@router.get("/vin/audi")
async def get_audi_vin_detail(req: Request) -> dict:
    vehicle_id = req.query_params.get("vehicleId")

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.audiusa.com/",
    }

    vin_post_data = {
        "operationName": "getVehicleInfoForWormwood",
        "variables": {
            "version": "2.0.0",
            "market": "US",
            "lang": "en",
            "id": f"{vehicle_id}",
        },
        "query": "query getVehicleInfoForWormwood($market: MarketType!, $lang: String!, $id: String!, $version: String) { getVehicleInfoForWormwood( market: $market lang: $lang id: $id version: $version ) { modelName trimName bodyType modelYear trimline gearType driveType modelMileage vehicleType market fuelType equipments { optionalEquipments { headline text imageUrl benefits __typename } standardEquipments { interior { headline text imageUrl __typename } exterior { headline text imageUrl __typename } assistanceSystems { headline text imageUrl __typename } technology { headline text imageUrl __typename } trimsAndPackages { headline text imageUrl __typename } performance { headline text imageUrl __typename } __typename } __typename } exteriorColor upholsteryColor interiorTileImage exteriorTileImage dealerName dealerNote staticDealerInfo { isDealerNoteVisible mapImage dagid __typename } vehicleMedia { mediaRequestString mediaImages { config imageType url __typename } __typename } technicalSpecifications { engineType displacement maxOutput maxTorque gearbox frontAxle rearAxle brakes steering unladenWeight grossWeightLimit tankCapacity luggageCompartmentCapacity topSpeed acceleration fuelType fuelData { fuel_petrol { unit urban extraUrban combined __typename } fuel_electrical { unit urban extraUrban combined __typename } __typename } __typename } __typename }}",  # noqa: B950
    }

    async with AsyncHTTPClient(
        base_url=audi_base_url,
        timeout_value=30.0,
        verify=verify_ssl,
    ) as http:
        v = await http.post(uri="/", headers=headers, post_data=vin_post_data)
        data = v.json()

    try:
        data["data"]["getVehicleInfoForWormwood"]
        return send_response(response_data=data, cache_control_age=3600)
    except KeyError:
        error_message = "An error occurred with the Audi inventory service"
        return error_response(error_message=error_message, error_data=data)
