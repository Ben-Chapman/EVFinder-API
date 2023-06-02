import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from src.libs.common_query_params import CommonInventoryQueryParams
from tests.test_helpers import generate_test_query_params
from main import app

client = TestClient(app)


@app.get("/api/inventory/tests")
def foo(req_params: CommonInventoryQueryParams = Depends()) -> dict:
    """This endpoint is used for query parameter validation testing"""
    return {}


def test_non_existent_route():
    r = client.get("/nothing-to-see-here")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "test_input, expected_status_code, assertion_message",
    [
        ("2022", 200, "Valid year"),
        ("2023", 200, "Valid year"),
        ("2021", 422, "Invalid year"),
        ("201", 422, "Invalid year, too short"),
        ("-2022", 422, "Invalid year, this is a negative value"),
        ("notayear", 422, "Invalid year, this is a string"),
        ("🤔", 422, "Invalid year, this is an emoji"),
    ],
)
def test_year_validation(test_input, expected_status_code, assertion_message):
    test_params = generate_test_query_params()
    test_params["year"] = test_input
    r = client.get("/api/inventory/tests", params=test_params)

    assert r.status_code == expected_status_code, assertion_message


@pytest.mark.parametrize(
    "test_input, expected_status_code, assertion_message",
    [
        # TODO:
        # Need to rethink validation for this case. The existing validations won't catch
        # numbers of len() < 5 where the number is > 500
        # ("1234", 422, "Zip not complete, too short"),
        ("notanumber", 422, "Zip should be a number"),
        ("🤔", 422, "Zip codes can't be emoji...yet"),
        ("00500", 422, "Zip code not valid (too low)"),
        ("99951", 422, "Zip code not valid (too high)"),
        ("0", 422, "Zip code not valid (too low, too short)"),
        ("-12345", 422, "Not a valid zip code"),
        ("98585-5002", 422, "Not a 5-digit zip code"),
        ("12345", 200, "Valid zip"),
        ("00501", 200, "Valid first zip code"),
        ("99950", 200, "Valid last zip code"),
    ],
)
def test_zip_validation(test_input, expected_status_code, assertion_message):
    test_params = generate_test_query_params()
    test_params["zip"] = test_input
    r = client.get("/api/inventory/tests", params=test_params)

    assert r.status_code == expected_status_code, assertion_message


@pytest.mark.parametrize(
    "test_input, expected_status_code, assertion_message",
    [
        ("0", 422, "Radius too small"),
        ("-1", 422, "Not a valid radius"),
        ("🤔", 422, "Not a valid radius"),
        ("1000", 422, "Radius too large"),
        ("1", 200, "Minimum radius"),
        ("999", 200, "Maximum radius"),
    ],
)
def test_radius_validation(test_input, expected_status_code, assertion_message):
    test_params = generate_test_query_params()
    test_params["radius"] = test_input
    r = client.get("/api/inventory/tests", params=test_params)

    assert r.status_code == expected_status_code, assertion_message


@pytest.mark.parametrize(
    "test_input, expected_status_code, assertion_message",
    [
        ("Z", 422, "Is not a valid model"),
        ("Ioniq 8", 422, "Is not a valid model"),
        ("Fahrzeug", 422, "Is not a valid model"),
        ("автомобіль", 422, "Is not a valid model"),
        ("12345", 422, "Is not a valid model"),
        ("Ioniq%205", 200, "Is a valid model"),
        ("Ioniq 5", 200, "Is a valid model"),
        ("Ioniq+5", 200, "Is a valid model"),
        ("Ioniq%206", 200, "Is a valid model"),
        ("Ioniq%20Phev", 200, "Is a valid model"),
        ("Kona%20Ev", 200, "Is a valid model"),
        ("Santa%20Fe%20Phev", 200, "Is a valid model"),
        ("Tucson%20Phev", 200, "Is a valid model"),
        ("N", 200, "Is a valid model"),
        ("V", 200, "Is a valid model"),
        ("F", 200, "Is a valid model"),
        ("R", 200, "Is a valid model"),
        ("T", 200, "Is a valid model"),
        ("GV60", 200, "Is a valid model"),
        ("ElectrifiedG80", 200, "Is a valid model"),
        ("ID.4", 200, "Is a valid model"),
        ("mache", 200, "Is a valid model"),
        ("Bolt EV", 200, "Is a valid model"),
        ("Bolt EUV", 200, "Is a valid model"),
        ("etron", 200, "Is a valid model"),
        ("etrongt", 200, "Is a valid model"),
        ("q4", 200, "Is a valid model"),
    ],
)
def test_model_validation(test_input, expected_status_code, assertion_message):
    test_params = generate_test_query_params()
    test_params["model"] = test_input

    r = client.get("/api/inventory/tests", params=test_params)

    assert r.status_code == expected_status_code, assertion_message
