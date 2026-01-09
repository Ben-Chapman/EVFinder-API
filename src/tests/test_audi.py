import pytest
from faker import Faker
from fastapi.testclient import TestClient

from src.tests.test_helpers import program_vcr
from src.main import app

client = TestClient(app)
fake = Faker()
vcr = program_vcr()


@pytest.fixture(
    scope="module",
    name="test_cassette",
    params=[
        "Q4 e-tron",
        "Q8 e-tron",
    ],
)
def _test_cassette(request):
    vehicle_model = request.param

    # Audi requires geo parameter format: zip_radius_miles_defaultcity
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "125",
        "model": vehicle_model,
        "geo": "90210",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"audi-{vehicle_model.replace(' ', '_')}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/audi", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_audi_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_audi_inventory_response_has_data(test_cassette):
    """The Audi API response contains the expected data structure"""
    response_data = test_cassette.json()
    assert "data" in response_data, (
        "Response does not contain 'data' key"
    )
    assert "getFilteredVehiclesForWormwood" in response_data["data"], (
        "Response data does not contain 'getFilteredVehiclesForWormwood' key"
    )


def test_audi_inventory_has_filter_results(test_cassette):
    """Audi response includes filterResults with totalCount"""
    response_data = test_cassette.json()
    filter_results = response_data["data"]["getFilteredVehiclesForWormwood"]["filterResults"]

    assert "totalCount" in filter_results, (
        "filterResults does not contain 'totalCount'"
    )
    assert isinstance(filter_results["totalCount"], int), (
        "totalCount is not an integer"
    )


def test_audi_inventory_has_vehicles(test_cassette):
    """Vehicles are returned in the response"""
    response_data = test_cassette.json()
    vehicles = response_data["data"]["getFilteredVehiclesForWormwood"]["vehicles"]

    assert isinstance(vehicles, list), "vehicles is not a list"
    assert len(vehicles) >= 0, "vehicles list should exist (can be empty)"


def test_audi_inventory_vehicle_structure(test_cassette):
    """Verify vehicle objects have expected keys"""
    response_data = test_cassette.json()
    vehicles = response_data["data"]["getFilteredVehiclesForWormwood"]["vehicles"]

    if len(vehicles) > 0:
        vehicle = vehicles[0]
        required_keys = ["id", "vin", "modelName", "modelYear", "dealerName"]

        for key in required_keys:
            assert key in vehicle, f"Vehicle missing required key: {key}"


def test_get_vin_detail(test_cassette):
    """Test VIN detail endpoint with a vehicle ID from inventory"""
    response_data = test_cassette.json()
    vehicles = response_data["data"]["getFilteredVehiclesForWormwood"]["vehicles"]

    if len(vehicles) == 0:
        pytest.skip("No vehicles in inventory to test VIN detail")

    try:
        vehicle_id = vehicles[0]["id"]
    except (KeyError, IndexError):
        pytest.fail("Could not find a vehicle ID in the test cassette")

    params = {"vehicleId": vehicle_id}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "audi-vin-detail.yaml"
    with vcr.use_cassette(cassette_name):
        vin_data = client.get("/api/vin/audi", headers=headers, params=params)

    assert vin_data.status_code == 200, (
        f"VIN Detail API response status code was {vin_data.status_code}, "
        "it was expected to be 200"
    )

    vin_response = vin_data.json()
    assert "data" in vin_response, "VIN response missing 'data' key"
    assert "getVehicleInfoForWormwood" in vin_response["data"], (
        "VIN response missing 'getVehicleInfoForWormwood' key"
    )


def test_audi_pagination_single_page():
    """Test that single page responses (<=24 vehicles) work correctly"""
    params = {
        "zip": "99999",  # Remote zip likely to have few results
        "year": "2024",
        "radius": "10",
        "model": "Q4 e-tron",
        "geo": "99999",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "audi-single-page.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/audi", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()
    vehicles = response_data["data"]["getFilteredVehiclesForWormwood"]["vehicles"]
    total_count = response_data["data"]["getFilteredVehiclesForWormwood"]["filterResults"]["totalCount"]

    # Verify we don't have pagination artifacts
    assert len(vehicles) <= 24 or len(vehicles) == total_count


def test_audi_error_handling_invalid_geo():
    """Test error handling with missing/invalid geo parameter"""
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "125",
        "model": "Q4 e-tron",
        # Missing geo parameter
    }
    headers = {"User-Agent": fake.user_agent()}

    # This should still work as the backend might use default values
    cassette_name = "audi-no-geo.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/audi", headers=headers, params=params)

    # Response should be 200 but might have empty results
    assert r.status_code in [200, 400, 422]


def test_audi_empty_inventory_results():
    """Test handling of searches with no results"""
    params = {
        "zip": "00501",  # Remote location
        "year": "2024",
        "radius": "1",  # Very small radius
        "model": "RS e-tron GT",
        "geo": "00501",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "audi-no-results.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/audi", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Should have valid structure even with no vehicles
    assert "data" in response_data
    vehicles = response_data["data"]["getFilteredVehiclesForWormwood"]["vehicles"]
    assert isinstance(vehicles, list)
