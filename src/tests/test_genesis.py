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
        "ElectrifiedG80",
        "GV60",
    ],
)
def _test_cassette(request):
    vehicle_model = request.param
    params = {"zip": "90210", "year": "2023", "radius": "125", "model": vehicle_model}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"genesis-{vehicle_model}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/genesis", headers=headers, params=params)
        # d = client.get("/api/dealer/genesis", headers=headers, params=params)
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
    """Do the Genesis API results indicate success"""
    assert (
        len(test_cassette.json()["Vehicles"]) >= 1
    ), "The number of vehicles returned was < 1"
    assert test_cassette.json()["Vehicles"][0]["Veh"][
        "VIN"
    ], "The inventory response does not contain a VIN"


def test_genesis_inventory_has_dealers():
    """Dealers with inventory are returned"""
    params = {
        "zip": "90210",
        "year": "2023",
        "radius": "125",
        "model": "ElectrifiedG80",
    }
    headers = {"User-Agent": fake.user_agent()}

    d = client.get("/api/dealer/genesis", headers=headers, params=params)
    assert (
        len(d.json()["dealers"]) >= 1
    ), "API response was a Success but no dealers have inventory"
