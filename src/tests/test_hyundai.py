import pytest
from faker import Faker
from fastapi.testclient import TestClient

from src.tests.test_helpers import program_vcr
from src.main import app

client = TestClient(app)
vcr = program_vcr()


@pytest.fixture(
    scope="module",
    name="test_cassette",
    params=[
        "Ioniq%205",
    ],
)
def _test_cassette(request):
    fake = Faker()
    vehicle_model = request.param

    params = {"zip": "00501", "year": "2023", "radius": "125", "model": vehicle_model}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"hyundai-{vehicle_model}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/hyundai", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_hyundai_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_hyundai_inventory_response_is_a_success(test_cassette):
    """The Hyundai API thinks our request was a success"""
    assert (
        test_cassette.json()["status"] == "SUCCESS"
    ), "'SUCCESS' was not found in the Hyundai Inventory response"


def test_hyundai_inventory_has_dealers(test_cassette):
    """Dealers with inventory are returned"""
    assert (
        len(test_cassette.json()["data"][0]["dealerInfo"]) >= 1
    ), "API response was a Success but no dealers have inventory"


def test_hyundai_inventory_dealer_has_inventory(test_cassette):
    """Dealers have inventory"""
    assert (
        len(test_cassette.json()["data"][0]["dealerInfo"][0]["vehicles"]) >= 1
    ), "API response was a Success but no dealers have inventory"


# def test_get_vin_detail():
#     pass


# def test_get_inventory_no_results():
#     pass


# def test_get_inventory_produces_error():
#     pass


# def test_get_vin_detail_produces_error():
#     pass
