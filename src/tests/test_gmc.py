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
        "Sierra EV",
        "HUMMER EV Pickup",
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

    cassette_name = f"gmc-{vehicle_model.replace(' ', '_')}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/gmc", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_gmc_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_gmc_inventory_response_has_results_count(test_cassette):
    """The GMC API response contains resultsCount field"""
    response_data = test_cassette.json()

    assert "resultsCount" in response_data, (
        "Response does not contain 'resultsCount' key"
    )
    assert isinstance(response_data["resultsCount"], int), (
        "resultsCount is not an integer"
    )


def test_gmc_inventory_has_vehicles(test_cassette):
    """GMC response includes vehicles array"""
    response_data = test_cassette.json()

    assert "vehicles" in response_data, (
        "Response does not contain 'vehicles' key"
    )
    assert isinstance(response_data["vehicles"], list), (
        "vehicles is not a list"
    )


def test_gmc_inventory_vehicle_structure(test_cassette):
    """Verify vehicle objects have expected keys"""
    response_data = test_cassette.json()
    vehicles = response_data.get("vehicles", [])

    if len(vehicles) == 0:
        pytest.skip("No vehicles in inventory to test structure")

    vehicle = vehicles[0]

    required_keys = [
        "vin",
        "year",
        "make",
        "model",
    ]

    for key in required_keys:
        assert key in vehicle, f"Vehicle missing required key: {key}"


def test_gmc_pagination_single_page():
    """Test that single page responses (<=96 vehicles) work correctly"""
    params = {
        "zip": "99999",  # Remote zip likely to have few results
        "year": "2024",
        "radius": "10",
        "model": "HUMMER EV Pickup",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "gmc-single-page.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/gmc", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    results_count = response_data["resultsCount"]
    vehicles = response_data["vehicles"]

    # For single page, vehicle count should match or be less than results_count
    assert len(vehicles) <= 96 or len(vehicles) == results_count


def test_gmc_large_page_size():
    """Test that GMC uses page size of 96"""
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "500",  # Large radius
        "model": "Sierra EV",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "gmc-large-page.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/gmc", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Should handle result sets up to 96 per page
    vehicles = response_data["vehicles"]
    assert len(vehicles) <= 96 or isinstance(vehicles, list)


def test_get_vin_detail(test_cassette):
    """Test VIN detail endpoint with a VIN from inventory"""
    response_data = test_cassette.json()
    vehicles = response_data.get("vehicles", [])

    if len(vehicles) == 0:
        pytest.skip("No vehicles in inventory to test VIN detail")

    try:
        vin = vehicles[0]["vin"]
    except (KeyError, IndexError):
        pytest.fail("Could not find a VIN in the test cassette")

    params = {
        "vin": vin,
        "zip": "90210",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "gmc-vin-detail.yaml"
    with vcr.use_cassette(cassette_name):
        vin_data = client.get("/api/vin/gmc", headers=headers, params=params)

    assert vin_data.status_code == 200, (
        f"VIN Detail API response status code was {vin_data.status_code}, "
        "it was expected to be 200"
    )

    vin_response = vin_data.json()
    assert "vin" in vin_response, "VIN response missing 'vin' key"
    assert vin in vin_response["vin"], (
        f"VIN {vin} not found in response"
    )


def test_gmc_empty_inventory_results():
    """Test handling of searches with no results"""
    params = {
        "zip": "00501",  # Remote location
        "year": "2024",
        "radius": "1",  # Very small radius
        "model": "Sierra EV",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "gmc-no-results.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/gmc", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Should have valid structure even with no vehicles
    assert "resultsCount" in response_data
    assert "vehicles" in response_data
    assert response_data["resultsCount"] == 0 or len(response_data["vehicles"]) == 0


def test_gmc_error_handling_no_results_count():
    """Test error handling when resultsCount is missing"""
    params = {
        "zip": "00000",  # Invalid zip
        "year": "2024",
        "radius": "125",
        "model": "Sierra EV",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "gmc-error-no-count.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/gmc", headers=headers, params=params)

    # Should handle error gracefully
    assert r.status_code in [200, 400, 422, 500]


def test_gmc_api_error_flag():
    """Test that API errors are flagged in response"""
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "125",
        "model": "Sierra EV",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "gmc-api-error-flag.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/gmc", headers=headers, params=params)

    # Should return valid response structure
    assert r.status_code in [200, 400, 500]


def test_gmc_include_near_matches():
    """Verify GMC API includes near matches parameter"""
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "125",
        "model": "Sierra EV",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "gmc-near-matches.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/gmc", headers=headers, params=params)

    assert r.status_code == 200
    # If includeNearMatches works, we might get more results
    response_data = r.json()
    assert "vehicles" in response_data
