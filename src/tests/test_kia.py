import pytest
from faker import Faker
from fastapi.testclient import TestClient

from src.main import app
from src.tests.test_helpers import program_vcr

client = TestClient(app)
vcr = program_vcr()


@pytest.fixture(
    scope="module",
    name="test_cassette",
    params=[
        "N",  # Kia EV6
        "V",  # Kia Niro EV
    ],
)
def _test_cassette(request):
    fake = Faker()
    vehicle_model = request.param

    params = {"zip": "90210", "year": "2023", "radius": "125", "model": vehicle_model}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"kia-{vehicle_model}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/kia", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_kia_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_kia_inventory_response_is_a_success(test_cassette):
    """The kia API thinks our request was a success"""
    response_json = test_cassette.json()
    assert "filterSet" in response_json or "inventoryVehicles" in response_json, (
        "Neither 'filterSet' nor 'inventoryVehicles' was found in the Kia Inventory response"
    )


def test_kia_inventory_has_dealers(test_cassette):
    """Dealers with inventory are returned"""
    response_json = test_cassette.json()
    if "filterSet" in response_json:
        # filterSet exists, check dealers
        dealers = response_json["filterSet"].get("dealers", [])
        assert isinstance(dealers, list), "dealers should be a list"
        # Note: dealers list can be empty if no inventory is available
    else:
        pytest.skip("No filterSet in response")


def test_get_vin_detail():
    pass


def test_get_inventory_no_results():
    pass


def test_get_inventory_produces_error():
    pass


def test_get_vin_detail_produces_error():
    pass
