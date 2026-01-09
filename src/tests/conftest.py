import os
import time
from unittest.mock import Mock, patch

import pytest
import vcr

cassette_dir = os.path.join(os.path.dirname(__file__), "cassettes")


def program_vcr():
    # Create cassettes directory if it doesn't exist
    if not os.path.exists(cassette_dir):
        os.makedirs(cassette_dir)

    for cassette in os.listdir(cassette_dir):
        if "yaml" in cassette:  # Only delete the cassette files
            delete_stale_cassette(cassette_name=cassette)

    _vcr = vcr.VCR(
        cassette_library_dir=cassette_dir,
        record_mode="new_episodes",
    )

    return _vcr


def delete_stale_cassette(
    cassette_name: str, delete_if_older_than_days: int = 30
) -> None:
    """We're using VCR.py to record the request / responses to the various manufacturer
    APIs, in order to facilitate offline testing, less-flakey and deterministic tests.
    As the manufacturer APIs are not under our control, I want to occasionally refresh
    the API responses to ensure our tests pass against the most recent version of a
    manufacturer API. If a VCR.py cassette is > delete_if_older_than_days days old,
    remove it before starting a test.

    Args:
        cassette_name (str): Name of the cassette file to delete.
        delete_if_older_than_days (int, optional): Delete a cassette file if older than
         this value. Defaults to 30.
    """

    cassette_file = f"{cassette_dir}/{cassette_name}"
    file_age_in_sec = time.time() - os.path.getmtime(cassette_file)

    if file_age_in_sec > (delete_if_older_than_days * 60 * 60):
        print(f"Deleting {cassette_file}")
        os.remove(cassette_file)


@pytest.fixture(autouse=True)
def mock_gcp_error_reporting():
    """Automatically mock GCP Error Reporting for all tests.

    This fixture runs for every test and prevents real GCP API calls.
    """
    mock_error_reporting = Mock()
    mock_client = Mock()

    # Mock the Client class and its methods
    mock_error_reporting.Client.return_value = mock_client
    mock_error_reporting.HTTPContext = Mock()
    mock_client.report.return_value = None

    # Patch at the point of import in the logger module
    with patch.dict(
        "sys.modules", {"google.cloud.error_reporting": mock_error_reporting}
    ):
        yield mock_error_reporting


@pytest.fixture
def mock_gcp_metadata():
    """Mock GCP metadata server responses for health check tests."""
    return {
        "instance": {
            "id": "12345678901234",
            "zone": "projects/123456789012/zones/us-central1-a",
        }
    }
