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
        "q4",  # Q4 e-tron
        "etrongt",  # e-tron GT
    ],
)
def _test_cassette(request):
    vehicle_model = request.param

    params = {
        "zip": "90210",
        "year": "2026",
        "radius": "125",
        "model": vehicle_model,
        # geo is provided as "lat_lng" by the frontend
        "geo": "34.06965_-118.396306",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = f"audi-{vehicle_model}.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/audi", headers=headers, params=params)

    return r


def test_api_returns_200(test_cassette):
    assert test_cassette.status_code == 200, (
        f"API response status code was "
        f"{test_cassette.status_code}, it was expected to be 200"
    )


def test_audi_inventory_response_is_json(test_cassette):
    try:
        test_cassette.json()
    except Exception:
        pytest.fail(f"API response is not valid JSON. It was: {test_cassette.text}")


def test_audi_inventory_response_has_data(test_cassette):
    """The Audi API response contains the expected data structure."""
    response_data = test_cassette.json()
    assert "data" in response_data, "Response does not contain 'data' key"
    assert "stockCarSearch" in response_data["data"], (
        "Response data does not contain 'stockCarSearch' key"
    )


def test_audi_inventory_has_result_count(test_cassette):
    """Audi response includes resultNumber indicating total available inventory."""
    response_data = test_cassette.json()
    stock_car_search = response_data["data"]["stockCarSearch"]

    assert "resultNumber" in stock_car_search, (
        "stockCarSearch does not contain 'resultNumber'"
    )
    assert isinstance(stock_car_search["resultNumber"], int), (
        "resultNumber is not an integer"
    )


def test_audi_inventory_has_cars(test_cassette):
    """Cars are returned in the response."""
    response_data = test_cassette.json()
    cars = response_data["data"]["stockCarSearch"]["results"]["cars"]

    assert isinstance(cars, list), "cars is not a list"


def test_audi_inventory_car_structure(test_cassette):
    """Verify car objects have expected keys."""
    response_data = test_cassette.json()
    cars = response_data["data"]["stockCarSearch"]["results"]["cars"]

    if len(cars) > 0:
        car = cars[0]
        assert "stockCar" in car, "Car missing 'stockCar' key"

        stock_car = car["stockCar"]
        required_keys = ["id", "vin", "model", "dealer"]
        for key in required_keys:
            assert key in stock_car, f"stockCar missing required key: {key}"


def test_audi_pagination_single_page():
    """Test that single page responses work correctly."""
    params = {
        "zip": "00501",
        "year": "2026",
        "radius": "10",
        "model": "q4",
        "geo": "40.9226_-72.6369",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "audi-single-page.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/audi", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()
    stock_car_search = response_data["data"]["stockCarSearch"]
    cars = stock_car_search["results"]["cars"]
    total_count = stock_car_search["resultNumber"]

    assert len(cars) <= total_count


def test_audi_empty_inventory_results():
    """Test handling of searches with no results."""
    params = {
        "zip": "00501",
        "year": "2026",
        "radius": "1",
        "model": "rsetrongt",
        "geo": "40.9226_-72.6369",
    }
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "audi-no-results.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/inventory/audi", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()
    assert "data" in response_data
    cars = response_data["data"]["stockCarSearch"]["results"]["cars"]
    assert isinstance(cars, list)


def test_audi_vin_detail():
    """VIN detail endpoint returns structured StockCarSearch data for a single VIN."""
    params = {"vehicleId": "WAUJ8BFW5S7901084"}
    headers = {"User-Agent": fake.user_agent()}

    cassette_name = "audi-vin-detail.yaml"
    with vcr.use_cassette(cassette_name):
        r = client.get("/api/vin/audi", headers=headers, params=params)

    assert r.status_code == 200
    response_data = r.json()
    assert "data" in response_data
    assert "stockCarSearch" in response_data["data"]

    cars = response_data["data"]["stockCarSearch"]["results"]["cars"]
    assert isinstance(cars, list)
    assert len(cars) > 0

    stock_car = cars[0]["stockCar"]
    assert "vin" in stock_car
    assert "titleText" in stock_car
    assert "colorInfo" in stock_car
