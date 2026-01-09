import pytest
from faker import Faker
from fastapi.testclient import TestClient

from src.tests.test_helpers import program_vcr
from src.main import app

client = TestClient(app)
vcr = program_vcr()


@pytest.fixture(scope="module", name="test_globals")
def _test_globals():
    fake = Faker()

    params = {"zip": "90210", "year": "2023", "radius": "125"}
    headers = {"User-Agent": fake.user_agent()}
    return params, headers


@pytest.fixture(
    scope="module",
    name="test_cassette",
    params=[
        "Bolt EV",
        "Bolt EUV",
    ],
)
def _test_cassette(request, test_globals):
    vehicle_model = request.param
    cassette_name = f"chevrolet-{vehicle_model}.yaml"
    params = {**test_globals[0], "model": vehicle_model}

    with vcr.use_cassette(cassette_name):
        r = client.get(
            "/api/inventory/chevrolet", headers=test_globals[1], params=params
        )

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_chevrolet_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_chevrolet_inventory_response_is_a_success(test_cassette):
    """The chevrolet API thinks our request was a success"""
    assert test_cassette.json()["data"][
        "listResponse"
    ], "No data was found in the Chevrolet Inventory response"


def test_chevrolet_inventory_has_inventory(test_cassette):
    """Dealers with inventory are returned"""
    assert (
        len(test_cassette.json()["data"]["listResponse"]) >= 1
    ), "API response was a Success but no dealers have inventory"


# def test_get_vin_detail():
#     assert "foo" == "bar"


# def test_get_inventory_no_results():
#     pass


# def test_get_inventory_produces_error():
#     pass


# def test_get_vin_detail_produces_error():
#     pass
