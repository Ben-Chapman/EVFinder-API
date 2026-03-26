from unittest.mock import MagicMock, patch

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
        "sierra ev",  # GMC Sierra EV
        "hummer ev pickup",  # GMC HUMMER EV Pickup
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

    cassette_map = {
        "sierra ev": "gmc-Sierra_EV.yaml",
        "hummer ev pickup": "gmc-HUMMER_EV_Pickup.yaml",
    }
    cassette_name = cassette_map.get(
        vehicle_model, f"gmc-{vehicle_model.replace(' ', '_')}.yaml"
    )
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


def test_gmc_inventory_response_is_a_success(test_cassette):
    """The GMC API response contains a data object with inventory results"""
    response_data = test_cassette.json()

    assert "data" in response_data, "Response does not contain 'data' key"
    assert "hits" in response_data["data"], "Response data does not contain 'hits' key"
    assert "count" in response_data["data"], (
        "Response data does not contain 'count' key"
    )


def test_gmc_inventory_has_inventory(test_cassette):
    """Vehicles are returned in the hits array"""
    assert len(test_cassette.json()["data"]["hits"]) >= 1, (
        "API response was a Success but no vehicles were returned"
    )


def test_gmc_inventory_all_vehicles_fetched(test_cassette):
    """All vehicles matching the search are returned, not just the first page"""
    data = test_cassette.json()["data"]
    assert len(data["hits"]) == data["count"], (
        f"Expected {data['count']} vehicles but got {len(data['hits'])}"
    )


def test_known_gmc_trims_are_in_set():
    """_KNOWN_GMC_TRIMS covers all expected Sierra EV and HUMMER EV trim names."""
    from src.routers.gmc import _KNOWN_GMC_TRIMS

    expected = {
        # Sierra EV
        "Elevation Standard Range",
        "Elevation Extended Range",
        "Denali Standard Range",
        "Extended Range Denali",
        "Max Range Denali",
        "AT4 Extended Range",
        "AT4 Max Range",
        "Denali Max Range",
        # HUMMER EV Pickup
        "2X",
        "3X",
    }
    assert expected.issubset(_KNOWN_GMC_TRIMS)


def test_unknown_trim_triggers_gcp_alert():
    """An alert is sent to GCP when a vehicle has a trim not in _KNOWN_GMC_TRIMS."""
    from src.routers.gmc import _log_unknown_trims

    hits = [{"variant": {"name": "Unknown Future Trim"}, "id": "1GT000000TEST001"}]
    request = MagicMock()
    request.headers.get.return_value = "TestAgent/1.0"
    request.url = "http://testserver/api/inventory/gmc"

    with patch("src.routers.gmc.send_error_to_gcp") as mock_alert:
        _log_unknown_trims(hits, request)
        mock_alert.assert_called_once()
        assert "Unknown Future Trim" in mock_alert.call_args[0][0]


def test_known_trim_does_not_trigger_gcp_alert():
    """No GCP alert is fired when all vehicle trims are in _KNOWN_GMC_TRIMS."""
    from src.routers.gmc import _log_unknown_trims

    hits = [
        {"variant": {"name": "2X"}, "id": "VIN1"},
        {"variant": {"name": "AT4 Extended Range"}, "id": "VIN2"},
        {"variant": {"name": "Denali Max Range"}, "id": "VIN3"},
    ]
    request = MagicMock()
    request.headers.get.return_value = "TestAgent/1.0"
    request.url = "http://testserver/api/inventory/gmc"

    with patch("src.routers.gmc.send_error_to_gcp") as mock_alert:
        _log_unknown_trims(hits, request)
        mock_alert.assert_not_called()


# TODO: Update VIN endpoint to use new GMC API before re-enabling this test
# def test_get_vin_detail(test_cassette):
#     pass
