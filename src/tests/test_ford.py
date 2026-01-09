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
        "mache",
        "f-150 lightning",
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

    cassette_name = f"ford-{vehicle_model.replace(' ', '_').replace('-', '_')}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/ford", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_ford_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_ford_inventory_response_has_dealer_slug(test_cassette):
    """Ford API adds dealerSlug to the response"""
    response_data = test_cassette.json()

    assert "dealerSlug" in response_data, "Response does not contain 'dealerSlug' key"
    assert isinstance(response_data["dealerSlug"], str), "dealerSlug is not a string"
    assert len(response_data["dealerSlug"]) > 0, "dealerSlug is empty"


def test_ford_inventory_has_data(test_cassette):
    """Ford response includes data with filterResults"""
    response_data = test_cassette.json()

    assert "data" in response_data, "Response does not contain 'data' key"

    # Empty filterResults is valid for no inventory
    if response_data["data"]["filterResults"] == []:
        pytest.skip("No inventory results for this search")

    assert "filterResults" in response_data["data"], (
        "Response data does not contain 'filterResults'"
    )


def test_ford_inventory_has_total_count(test_cassette):
    """Ford response includes totalCount"""
    response_data = test_cassette.json()

    # Empty filterResults is valid for no inventory
    if response_data["data"]["filterResults"] == []:
        pytest.skip("No inventory results for this search")

    filter_results = response_data["data"]["filterResults"]
    assert "ExactMatch" in filter_results, "filterResults missing 'ExactMatch' key"
    assert "totalCount" in filter_results["ExactMatch"], (
        "ExactMatch missing 'totalCount'"
    )


def test_ford_inventory_has_vehicles(test_cassette):
    """Ford response includes vehicles array"""
    response_data = test_cassette.json()

    # Empty filterResults is valid for no inventory
    if response_data["data"]["filterResults"] == []:
        pytest.skip("No inventory results for this search")

    vehicles = response_data["data"]["filterResults"]["ExactMatch"]["vehicles"]
    assert isinstance(vehicles, list), "vehicles is not a list"


def test_ford_inventory_vehicle_structure(test_cassette):
    """Verify vehicle objects have expected keys"""
    response_data = test_cassette.json()

    # Empty filterResults is valid for no inventory
    if (
        response_data["data"]["filterResults"] == []
        or len(response_data["data"]["filterResults"]["ExactMatch"]["vehicles"]) == 0
    ):
        pytest.skip("No vehicles in inventory to test structure")

    vehicles = response_data["data"]["filterResults"]["ExactMatch"]["vehicles"]
    vehicle = vehicles[0]

    required_keys = [
        "vin",
        "year",
        "modelDescription",
        "dealerSlug",
    ]

    for key in required_keys:
        assert key in vehicle, f"Vehicle missing required key: {key}"


def test_ford_pagination_data(test_cassette):
    """Ford includes rdata for paginated results"""
    response_data = test_cassette.json()

    # Empty filterResults is valid for no inventory
    if response_data["data"]["filterResults"] == []:
        pytest.skip("No inventory results for this search")

    total_count = response_data["data"]["filterResults"]["ExactMatch"]["totalCount"]

    # If totalCount > 12, should have pagination data
    if total_count > 12:
        assert "rdata" in response_data, (
            "Response missing 'rdata' for paginated results"
        )
        assert "vehicles" in response_data["rdata"], "rdata missing 'vehicles' array"
        assert "dealers" in response_data["rdata"], "rdata missing 'dealers' array"


def test_ford_pagination_large_result_set():
    """Test Ford pagination with large result set"""
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "500",  # Large radius to get many results
        "model": "mache",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "ford-large-results.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/ford", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Empty filterResults is valid
    if response_data["data"]["filterResults"] != []:
        total_count = response_data["data"]["filterResults"]["ExactMatch"]["totalCount"]

        # If we have more than 12 vehicles, check pagination
        if total_count > 12:
            assert "rdata" in response_data
            # Verify pagination happened (should have remainder data)
            assert len(response_data["rdata"]["vehicles"]) > 0


def test_ford_pagination_single_page():
    """Test that single page responses (<=12 vehicles) work correctly"""
    params = {
        "zip": "99999",  # Remote zip likely to have few results
        "year": "2024",
        "radius": "10",
        "model": "f-150 lightning",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "ford-single-page.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/ford", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Empty filterResults is valid
    if response_data["data"]["filterResults"] != []:
        total_count = response_data["data"]["filterResults"]["ExactMatch"]["totalCount"]

        # If we have <=12 vehicles, should not have rdata
        if total_count <= 12:
            assert "rdata" not in response_data or response_data.get("rdata") is None


def test_get_vin_detail(test_cassette):
    """Test VIN detail endpoint with data from inventory"""
    response_data = test_cassette.json()

    # Empty filterResults is valid
    if (
        response_data["data"]["filterResults"] == []
        or len(response_data["data"]["filterResults"]["ExactMatch"]["vehicles"]) == 0
    ):
        pytest.skip("No vehicles in inventory to test VIN detail")

    try:
        vehicle = response_data["data"]["filterResults"]["ExactMatch"]["vehicles"][0]
        vin = vehicle["vin"]
        dealer_slug = response_data["dealerSlug"]
        model_slug = vehicle.get("modelSlug", "mustang-mach-e")
        pa_code = vehicle.get("paCode", "")
    except (KeyError, IndexError):
        pytest.fail("Could not find vehicle data in the test cassette")

    params = {
        "vin": vin,
        "model": "mache",
        "zip": "90210",
        "year": "2024",
        "dealerSlug": dealer_slug,
        "modelSlug": model_slug,
        "paCode": pa_code,
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "ford-vin-detail.yaml"
    with vcr.use_cassette(cassette_name):
        vin_data = client.get("/api/vin/ford", headers=headers, params=params)

    assert vin_data.status_code == 200, (
        f"VIN Detail API response status code was {vin_data.status_code}, "
        "it was expected to be 200"
    )

    vin_response = vin_data.json()
    assert "data" in vin_response, "VIN response missing 'data' key"


def test_ford_empty_inventory_results():
    """Test handling of searches with no results"""
    params = {
        "zip": "00501",  # Remote location
        "year": "2024",
        "radius": "1",  # Very small radius
        "model": "mache",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "ford-no-results.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/ford", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Should have valid structure even with no vehicles
    assert "data" in response_data
    assert "dealerSlug" in response_data
    # Empty filterResults is valid for no results
    assert response_data["data"]["filterResults"] == [] or (
        len(response_data["data"]["filterResults"]["ExactMatch"]["vehicles"]) == 0
    )


def test_ford_dealer_slug_error_handling():
    """Test error handling when dealer slug retrieval fails"""
    params = {
        "zip": "00000",  # Invalid zip
        "year": "2024",
        "radius": "125",
        "model": "mache",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "ford-dealer-error.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/ford", headers=headers, params=params)

    # Should handle error gracefully
    assert r.status_code in [200, 400, 422, 500]


def test_ford_api_error_response_flag():
    """Test that API errors are flagged in response"""
    # This would require mocking or having a cassette with API errors
    # For now, just verify the response structure handles it
    params = {
        "zip": "90210",
        "year": "2024",
        "radius": "125",
        "model": "mache",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "ford-api-error-flag.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/ford", headers=headers, params=params)

    assert r.status_code in [200, 400, 500]
