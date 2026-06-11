import pytest
from faker import Faker
from fastapi.testclient import TestClient

from src.main import app
from src.tests.test_helpers import program_vcr

client = TestClient(app)
fake = Faker()
vcr = program_vcr()

# The single-letter UI model value maps to the three-letter series code the Kia
# inventory API expects. Asserting the returned filterSet.series proves the mapping.
expected_series = {
    "N": "NAE",  # EV6
    "V": "GAE",  # Niro EV
}


@pytest.fixture(
    scope="module",
    name="test_cassette",
    params=[
        "N",  # Kia EV6
        "V",  # Kia Niro EV
    ],
)
def _test_cassette(request):
    vehicle_model = request.param

    params = {"zip": "90210", "year": "2026", "radius": "125", "model": vehicle_model}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"kia-{vehicle_model}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/kia", headers=headers, params=params)

    return r, vehicle_model


def test_api_returns_200(test_cassette):
    response, _ = test_cassette
    assert response.status_code == 200, (
        f"API response status code was "
        f"{response.status_code}, it was expected to be 200"
    )


def test_kia_inventory_response_is_json(test_cassette):
    response, _ = test_cassette
    try:
        response.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {response.text}")


def test_kia_inventory_series_is_mapped(test_cassette):
    """The single-letter UI model is mapped to the three-letter Kia series code."""
    response, model = test_cassette
    series = response.json().get("filterSet", {}).get("series")
    assert series == expected_series[model], (
        f"Expected series '{expected_series[model]}' for model '{model}', "
        f"but the Kia response reported series '{series}'"
    )


def test_kia_inventory_has_vehicles(test_cassette):
    """Vehicles are returned under the inventoryVehicles key"""
    response, _ = test_cassette
    body = response.json()
    assert "inventoryVehicles" in body and len(body["inventoryVehicles"]) >= 1, (
        "API response was a success but no vehicles were returned"
    )


def test_get_vin_detail(test_cassette):
    """A VIN from the inventory results resolves through the new /vin/kia endpoint"""
    response, _ = test_cassette
    vehicles = response.json().get("inventoryVehicles", [])
    if not vehicles:
        pytest.skip("No inventory available to derive a VIN for the VIN detail test")

    vin = vehicles[0]["vin"]
    params = {"zip": "90210", "vin": vin}
    headers = {"User-Agent": fake.user_agent()}

    with vcr.use_cassette(f"kia-vin-{vin}.yaml"):
        vin_response = client.get("/api/vin/kia", headers=headers, params=params)

    assert vin_response.status_code == 200, (
        f"VIN Detail API response status code was {vin_response.status_code}, "
        "it was expected to be 200"
    )

    returned_vin = vin_response.json()["vehicles"][0]["vin"]
    assert returned_vin == vin, (
        "VIN found in the inventory response does not match the VIN detail: "
        f"{vin} != {returned_vin}"
    )


def test_no_inventory_for_unrecognized_vehicle():
    """A search for a year/model the Kia API does not recognize returns a 200 with a
    non-JSON error string. The EV Finder API should report no inventory, not an error.
    """
    params = {"zip": "07040", "year": "2027", "radius": "50", "model": "P"}
    headers = {"User-Agent": fake.user_agent()}

    with vcr.use_cassette("kia-no-inventory-unrecognized.yaml"):
        r = client.get("/api/inventory/kia", headers=headers, params=params)

    assert r.status_code == 200, (
        f"API response status code was {r.status_code}, it was expected to be 200"
    )
    assert r.json() == {}, "An unrecognized vehicle search should return no inventory"


def test_no_inventory_when_no_dealers_in_radius():
    """A valid search that returns nationwide near-matches with no dealers in range
    (empty filterSet.dealers) should report no inventory rather than crash the UI.
    """
    params = {"zip": "07040", "year": "2026", "radius": "1", "model": "N"}
    headers = {"User-Agent": fake.user_agent()}

    with vcr.use_cassette("kia-no-inventory-radius.yaml"):
        r = client.get("/api/inventory/kia", headers=headers, params=params)

    assert r.status_code == 200, (
        f"API response status code was {r.status_code}, it was expected to be 200"
    )
    assert r.json() == {}, (
        "A search with no dealers in range should return no inventory"
    )
