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
        "GV60",  # Genesis GV60
    ],
)
def _test_cassette(request):
    vehicle_model = request.param

    # The v2 API ignores year; it is sent for parity with a real EV Finder search.
    params = {"zip": "90210", "year": "2026", "radius": "125", "model": vehicle_model}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"genesis-{vehicle_model}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/genesis", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_genesis_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_genesis_inventory_response_is_a_success(test_cassette):
    """The EV Finder API reports the search was a success"""
    assert test_cassette.json()["status"] == "SUCCESS", (
        "'SUCCESS' was not found in the Genesis Inventory response"
    )


def test_genesis_inventory_has_vehicles(test_cassette):
    """Vehicles are returned as a flat list under the data key"""
    data = test_cassette.json()["data"]
    assert isinstance(data, list) and len(data) >= 1, (
        "API response was a Success but no vehicles were returned"
    )


def test_genesis_inventory_vehicles_have_required_fields(test_cassette):
    """Each vehicle carries the fields the inventory table renders"""
    vehicle = test_cassette.json()["data"][0]
    for field in ("VIN", "SortablePrice", "ExtColorDesc", "DlrName", "Distance"):
        assert field in vehicle, (
            f"Expected field '{field}' was missing from a vehicle record"
        )


def test_get_vin_detail(test_cassette):
    try:
        vin_for_test = test_cassette.json()["data"][0]["VIN"]
    except Exception:
        pytest.fail("Could not find a VIN in the test cassette")

    params = {"zip": "90210", "vin": vin_for_test}
    headers = {"User-Agent": fake.user_agent()}
    vin_data = client.get("/api/vin/genesis", headers=headers, params=params)

    assert vin_data.status_code == 200, (
        f"VIN Detail API response status code was {vin_data.status_code}, "
        "it was expected to be 200"
    )

    assert vin_for_test == vin_data.json()["data"][0]["Vehicle"][0]["VIN"], (
        "VIN found in the inventory response does not match the VIN detail: "
        f"{vin_for_test} != {vin_data.json()['data'][0]['Vehicle'][0]['VIN']}"
    )
