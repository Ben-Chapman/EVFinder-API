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
        "lyriq",  # Cadillac Lyriq
        "escalade iq",  # Cadillac Escalade IQ
    ],
)
def _test_cassette(request):
    vehicle_model = request.param

    params = {
        "zip": "90210",
        "year": "2025",
        "radius": "125",
        "model": vehicle_model,
    }
    headers = {"User-Agent": fake.user_agent()}

    # Map to cassette names which use the old format
    cassette_map = {
        "lyriq": "cadillac-Lyriq.yaml",
        "escalade iq": "cadillac-Escalade_IQ.yaml",
    }
    cassette_name = cassette_map.get(
        vehicle_model, f"cadillac-{vehicle_model.replace(' ', '_')}.yaml"
    )
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/cadillac", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_cadillac_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_cadillac_inventory_response_has_status(test_cassette):
    """The Cadillac API response contains status field"""
    response_data = test_cassette.json()

    # Empty dict is valid for no results
    if response_data == {}:
        pytest.skip("No inventory results for this search")

    assert "status" in response_data, "Response does not contain 'status' key"


def test_cadillac_inventory_has_data(test_cassette):
    """Cadillac response includes data with hits array"""
    response_data = test_cassette.json()

    # Empty dict is valid for no results
    if response_data == {}:
        pytest.skip("No inventory results for this search")

    assert "data" in response_data, "Response does not contain 'data' key"
    assert "hits" in response_data["data"], (
        "Response data does not contain 'hits' array"
    )


def test_cadillac_inventory_has_count(test_cassette):
    """Cadillac response includes count of total vehicles"""
    response_data = test_cassette.json()

    # Empty dict is valid for no results
    if response_data == {}:
        pytest.skip("No inventory results for this search")

    assert "count" in response_data["data"], "Response data does not contain 'count'"
    assert isinstance(response_data["data"]["count"], int), "count is not an integer"


def test_cadillac_inventory_vehicle_structure(test_cassette):
    """Verify vehicle objects have expected keys"""
    response_data = test_cassette.json()

    # Empty dict is valid for no results
    if response_data == {} or len(response_data.get("data", {}).get("hits", [])) == 0:
        pytest.skip("No vehicles in inventory to test structure")

    hits = response_data["data"]["hits"]
    vehicle = hits[0]

    required_keys = ["id", "make", "model", "year", "type", "dealer"]

    for key in required_keys:
        assert key in vehicle, f"Vehicle missing required key: {key}"


def test_cadillac_inventory_has_facets(test_cassette):
    """Cadillac response includes facets data"""
    response_data = test_cassette.json()

    # Empty dict is valid for no results
    if response_data == {}:
        pytest.skip("No inventory results for this search")

    assert "facets" in response_data, "Response does not contain 'facets' key"


def test_cadillac_pagination_single_page():
    """Test that single page responses (<=20 vehicles) work correctly"""
    params = {
        "zip": "99999",  # Remote zip likely to have few results
        "year": "2025",
        "radius": "10",
        "model": "lyriq",  # Cadillac Lyriq
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "cadillac-single-page.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/cadillac", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()

    # Empty dict is valid for no results
    if response_data != {}:
        hits = response_data["data"]["hits"]
        count = response_data["data"]["count"]

        # For single page, hits length should match count
        assert len(hits) <= 20 or len(hits) == count


def test_get_vin_detail(test_cassette):
    """Test VIN detail endpoint with a VIN from inventory"""
    response_data = test_cassette.json()

    # Empty dict is valid for no results
    if response_data == {} or len(response_data.get("data", {}).get("hits", [])) == 0:
        pytest.skip("No vehicles in inventory to test VIN detail")

    try:
        vehicle = response_data["data"]["hits"][0]
        vin = vehicle["id"]
        model = vehicle["model"]
        year = str(vehicle["year"])
    except KeyError, IndexError:
        pytest.fail("Could not find vehicle data in the test cassette")

    params = {
        "vin": vin,
        "model": model,
        "year": year,
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "cadillac-vin-detail.yaml"
    with vcr.use_cassette(cassette_name):
        vin_data = client.get("/api/vin/cadillac", headers=headers, params=params)

    assert vin_data.status_code == 200, (
        f"VIN Detail API response status code was {vin_data.status_code}, "
        "it was expected to be 200"
    )

    vin_response = vin_data.json()
    assert "data" in vin_response, "VIN response missing 'data' key"
    assert vin in vin_response["data"]["id"], (
        f"VIN {vin} not found in response ID {vin_response['data']['id']}"
    )


def test_cadillac_empty_inventory_results():
    """Test handling of searches with no results (inventory.notFound)"""
    params = {
        "zip": "00501",  # Remote location
        "year": "2025",
        "radius": "1",  # Very small radius
        "model": "lyriq",  # Cadillac Lyriq
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "cadillac-no-results.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/cadillac", headers=headers, params=params)

    assert r.status_code == 200

    response_data = r.json()
    # Cadillac returns empty dict for no results
    assert response_data == {} or (
        "data" in response_data and response_data["data"]["count"] == 0
    )


def test_cadillac_error_handling_invalid_year():
    """Test error handling with invalid year"""
    params = {
        "zip": "90210",
        "year": "2020",  # Too old for Cadillac EVs
        "radius": "125",
        "model": "Lyriq",
    }
    headers = {"User-Agent": fake.user_agent()}

    r = client.get("/api/inventory/cadillac", headers=headers, params=params)

    # Should return 422 validation error or 200 with no results
    assert r.status_code in [200, 422]


def test_cadillac_custom_headers():
    """Verify Cadillac API uses required custom headers"""
    params = {
        "zip": "90210",
        "year": "2025",
        "radius": "125",
        "model": "Lyriq",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "cadillac-headers-test.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/cadillac", headers=headers, params=params)

    # If custom headers are missing/incorrect, API would return error
    assert r.status_code == 200
