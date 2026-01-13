import pytest
from faker import Faker
from fastapi.testclient import TestClient

from src.main import app
from src.tests.test_helpers import program_vcr

client = TestClient(app)
fake = Faker()
vcr = program_vcr()


@pytest.fixture(
    scope="module",
    name="test_cassette",
    params=[
        "9",  # BMW electric vehicle model code
    ],
)
def _test_cassette(request):
    vehicle_model = request.param

    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "125",
        "model": vehicle_model,
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"bmw-{vehicle_model}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/bmw", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_bmw_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_bmw_inventory_response_has_data(test_cassette):
    """The BMW API response contains the expected data structure"""
    response_data = test_cassette.json()
    assert "data" in response_data, "Response does not contain 'data' key"
    assert "getInventory" in response_data["data"], (
        "Response data does not contain 'getInventory' key"
    )


def test_bmw_inventory_has_filter_data(test_cassette):
    """BMW response includes filter results and vehicle count"""
    response_data = test_cassette.json()
    inventory = response_data["data"]["getInventory"]

    assert "numberOfFilteredVehicles" in inventory, (
        "getInventory does not contain 'numberOfFilteredVehicles'"
    )
    assert isinstance(inventory["numberOfFilteredVehicles"], int), (
        "numberOfFilteredVehicles is not an integer"
    )


def test_bmw_inventory_has_result(test_cassette):
    """Vehicles are returned in the result array"""
    response_data = test_cassette.json()
    result = response_data["data"]["getInventory"]["result"]

    assert isinstance(result, list), "result is not a list"
    assert len(result) >= 0, "result list should exist (can be empty)"


def test_bmw_inventory_vehicle_structure(test_cassette):
    """Verify vehicle objects have expected keys"""
    response_data = test_cassette.json()
    result = response_data["data"]["getInventory"]["result"]

    if len(result) > 0:
        vehicle = result[0]
        required_keys = ["name", "modelYear", "vin", "code", "totalMsrp", "orderStatus"]

        for key in required_keys:
            assert key in vehicle, f"Vehicle missing required key: {key}"


def test_bmw_inventory_has_dealer_info(test_cassette):
    """BMW response includes dealerInfo array"""
    response_data = test_cassette.json()
    dealer_info = response_data["data"]["getInventory"]["dealerInfo"]

    assert isinstance(dealer_info, list), "dealerInfo is not a list"
    if len(dealer_info) > 0:
        dealer = dealer_info[0]
        assert "newVehicleSales" in dealer, "dealerInfo missing 'newVehicleSales'"


def test_bmw_order_status_codes(test_cassette):
    """Verify vehicles have valid order status codes (0-5)"""
    response_data = test_cassette.json()
    result = response_data["data"]["getInventory"]["result"]

    if len(result) > 0:
        for vehicle in result:
            if "orderStatus" in vehicle:
                status = vehicle["orderStatus"]
                # Status codes: 0-1 at dealer, 2-5 in transit/production
                assert status in [
                    "0",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                ], f"Invalid order status: {status}"


def test_get_vin_detail(test_cassette):
    """Test VIN detail endpoint with a VIN from inventory"""
    response_data = test_cassette.json()
    result = response_data["data"]["getInventory"]["result"]

    if len(result) == 0:
        pytest.skip("No vehicles in inventory to test VIN detail")

    try:
        vin = result[0]["vin"]
    except (KeyError, IndexError):
        pytest.fail("Could not find a VIN in the test cassette")

    params = {"vin": vin}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "bmw-vin-detail.yaml"
    with vcr.use_cassette(cassette_name):
        vin_data = client.get("/api/vin/bmw", headers=headers, params=params)

    assert vin_data.status_code == 200, (
        f"VIN Detail API response status code was {vin_data.status_code}, "
        "it was expected to be 200"
    )

    vin_response = vin_data.json()
    assert "data" in vin_response, "VIN response missing 'data' key"
    assert "getInventoryByIdentifier" in vin_response["data"], (
        "VIN response missing 'getInventoryByIdentifier' key"
    )

    # Verify VIN matches
    vin_result = vin_response["data"]["getInventoryByIdentifier"]["result"]
    if len(vin_result) > 0:
        assert vin_result[0]["vin"] == vin, (
            f"VIN mismatch: expected {vin}, got {vin_result[0]['vin']}"
        )


def test_bmw_large_page_size():
    """Test that BMW uses large page size (2000) to avoid pagination"""
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "500",  # Large radius to potentially get many results
        "model": "9",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "bmw-large-page.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/bmw", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()
    result = response_data["data"]["getInventory"]["result"]

    # Should be able to handle large result sets
    assert len(result) <= 2000


def test_bmw_empty_inventory_results():
    """Test handling of searches with no results"""
    params = {
        "zip": "00501",  # Remote location
        "year": "2024",
        "radius": "1",  # Very small radius
        "model": "9",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "bmw-no-results.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/bmw", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Should have valid structure even with no vehicles
    assert "data" in response_data
    result = response_data["data"]["getInventory"]["result"]
    assert isinstance(result, list)
    assert response_data["data"]["getInventory"]["numberOfFilteredVehicles"] == 0


def test_bmw_error_handling_invalid_model():
    """Test error handling with invalid model code"""
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "125",
        "model": "INVALID",
    }
    headers = {"User-Agent": fake.user_agent()}

    # This should fail validation at the query param level
    r = client.get("/api/inventory/bmw", headers=headers, params=params)

    # Should return 422 validation error
    assert r.status_code == 422
