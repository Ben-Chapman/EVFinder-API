from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = True
bmw_base_url = "https://www.bmwusa.com/inventory/graphql"


@router.get("/inventory/bmw")
async def get_bmw_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    # The BMW API has a pageSize attribute which is 24 by default. Setting a larger
    # pageSize to avoid API request pagination
    max_page_size = 2000

    zip_code = str(common_params.zip)
    model = common_params.model
    radius = str(common_params.radius)

    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.bmwusa.com/inventory.html",
    }

    inventory_post_data = {
        "query": "query inventory {getInventory(zip: "
        + f'"{zip_code}"'
        + ", bucket: BYO, filter: { locatorRange: "
        + radius
        + " excludeStopSale: false series: "
        + f'"{model}"'
        # Order statuses 0 and 1: Vehicle is at the dealership
        # 2, 3, 4, and 5: Vehicle is in transit or in production"
        + ', statuses:["0","1","2","3","4","5"] }, sorting: [{order: ASC, criteria: DISTANCE_TO_LOCATOR_ZIP},{order:ASC,criteria:PRICE}] pagination: {pageIndex: 1, '  # noqa: B950
        + f"pageSize: {max_page_size}"
        + "}) { numberOfFilteredVehicles pageNumber totalPages errorCode filter { modelsWithSeries { series { code name } model { code name } } } dealerInfo { centerID newVehicleSales { dealerName distance longitude locationID dealerURL phoneNumber address { lineOne lineTwo city state zipcode } } } result { name modelYear sold daysOnLot orderType dealerEstArrivalDate marketingText technicalText interiorGenericColor exteriorGenericColor hybridFlag sportsFlag vehicleDetailsPage milesPerGallon milesPerGallonEqv code bodyStyle { name } engineDriveType { name } series { name code } qualifiedModelCode technicalText totalMsrp dealerId dealerLocation distanceToLocatorZip orderStatus vin initialCOSYURL cosy { panoramaViewUrlPart walkaround360DegViewUrlPart } vehicleDetailsPage vehicleProcessingCenter isAtPmaDealer } } }"  # noqa: B950
    }

    async with AsyncHTTPClient(
        base_url=bmw_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        inv = await http.post(
            uri="/",
            headers=headers,
            post_data=inventory_post_data,
        )

    try:
        data = inv.json()
    except ValueError:
        return error_response(
            error_message=f"An error occurred with the BMW API: {inv.text}"
        )
    try:
        # If the inventory request was successful, even if 0 vehicles are returned
        # the response will have the ['getInventory'] dict, so validating that
        data["data"]["getInventory"]
        return send_response(
            response_data=data,
            cache_control_age=3600,
        )
    except KeyError:
        print(data)
        error_message = "An error occurred with the BMW API"
        return error_response(error_message=error_message, error_data=data)


@router.get("/vin/bmw")
async def get_bmw_vin_detail(req: Request) -> dict:
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "Referer": "https://www.bmwusa.com/inventory/",
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
        base_url=bmw_base_url,
        timeout_value=30.0,
        verify=verify_ssl,
    ) as http:
        v = await http.post(uri="/", headers=headers, post_data=vin_post_data)
        data = v.json()

    if len(data[0]["data"]["getInventoryByIdentifier"]["result"]) > 0:
        return send_response(response_data=data[0], cache_control_age=3600)
    else:
        error_message = "An error occurred with the  BMW API"
        return error_response(error_message=error_message, error_data=data)
