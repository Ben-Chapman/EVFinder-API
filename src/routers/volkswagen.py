from fastapi import APIRouter, Depends, Request

from src.libs.common_query_params import CommonInventoryQueryParams
from src.libs.responses import error_response, send_response
from src.libs.http import AsyncHTTPClient

router = APIRouter(prefix="/api")
verify_ssl = False
vw_base_url = "https://api.vw.com/graphql"


@router.get("/inventory/volkswagen")
async def get_volkswagen_inventory(
    req: Request, common_params: CommonInventoryQueryParams = Depends()
) -> dict:
    """"""
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.vw.com/",
    }

    inventory_post_data = (
        {
            "operationName": "InventoryData",
            "variables": {
                "zipcode": common_params.zip,
                "distance": common_params.radius,
                "pageSize": 1000,
                "pageNumber": 0,
                "sortBy": "",
                "filters": str(
                    {
                        "modelName": [common_params.model],
                        "modelYear": [common_params.year],
                    }
                ),
            },
            "query": "query InventoryData($zipcode: String, $distance: Int, $pageSize: Int, $pageNumber: Int, $sortBy: String, $filters: String) { inventory: getPagedInventoryByZipAndDistanceAndFilters( zipcode: $zipcode distance: $distance pageSize: $pageSize pageNumber: $pageNumber sortBy: $sortBy filters: $filters ) { modelYear totalPages totalVehicles vehicles { vin model msrp modelYear exteriorColorDescription factoryExteriorCode interiorColorDescription factoryInteriorCode mpgCity subTrimLevel engineDescription mpgHighway trimLevel onlineSalesURL dealerEnrollmentStatusInd inTransit dealer { dealerid name url distance address1 city state postalcode phone aor __typename } highlightFeatures { code name __typename } __typename } dealers { dealerid name url distance address1 city state postalcode phone aor __typename } aorDealer { dealerid name url distance address1 city state postalcode phone aor __typename } aorVehicle { vin model msrp modelYear exteriorColorDescription factoryExteriorCode interiorColorDescription factoryInteriorCode mpgCity subTrimLevel engineDescription mpgHighway trimLevel onlineSalesURL dealerEnrollmentStatusInd inTransit dealer { dealerid name url distance address1 city state postalcode phone aor __typename } highlightFeatures { code name __typename } __typename } filter { modelName filterAttributes { transmissionType { key value __typename } exteriorColor { key value __typename } interiorColor { key value __typename } modelYear { key value __typename } trimLevel { key value __typename } dealers { key value __typename } models { key value __typename } __typename } __typename } __typename }}",  # noqa: B950
        },
    )
    async with AsyncHTTPClient(
        base_url=vw_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        inv = await http.post(uri="/", headers=headers, post_data=inventory_post_data)

        data = inv.json()

        try:
            # If the inventory request was successful, even if 0 vehicles are returned
            # the response will have the ['inventory'] dict, so validating that
            data[0]["data"]["inventory"]
            return send_response(response_data=data[0])
        except KeyError:
            return error_response(
                error_message="An error occurred with the Volkswagen API",
                error_data=data,
            )


@router.get("/vin/volkswagen")
async def get_hyundai_vin_detail(req: Request) -> dict:
    zip_code = req.query_params.get("zip")
    vin = req.query_params.get("vin")

    # We'll use the requesting UA to make the request to the Volkswagen APIs
    headers = {
        "User-Agent": req.headers.get("User-Agent"),
        "referer": "https://www.vw.com/",
    }

    vin_post_data = {
        "operationName": "VehicleData",
        "variables": {"vin": vin, "zipcode": zip_code},
        "query": "query VehicleData($vin: String, $zipcode: String) { vehicle: getVehicleByVinAndZip(vin: $vin, zipcode: $zipcode) { vin model modelCode modelYear modelVersion carlineKey msrp mpgCity subTrimLevel engineDescription exteriorColorDescription exteriorColorCode interiorColorDescription interiorColorCode factoryExteriorCode factoryInteriorCode mpgHighway trimLevel mediaAssets { view type url __typename } onlineSalesURL dealerEnrollmentStatusInd highlightFeatures { code name __typename } factoryModelYear dealerInstalledAccessories { optionCode optionDescription optionLongDescription price imageUrl __typename } dealer { dealerid name dealername address1 city state postalcode country url phone distance aor __typename } specifications { optionCode optionDescription salesFamily __typename } destinationCharge __typename }}\n",  # noqa: B950
    }

    async with AsyncHTTPClient(
        base_url=vw_base_url, timeout_value=30.0, verify=verify_ssl
    ) as http:
        vin = await http.post(uri="/", headers=headers, post_data=vin_post_data)
        data = vin.json()

    if len(data["data"]["vehicle"]) > 0:
        return send_response(response_data=data)
    else:
        return error_response(
            error_message="An error occurred with the Volkswagen API", error_data=data
        )
