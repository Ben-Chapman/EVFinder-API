import os
from unittest.mock import MagicMock, Mock

import vcr


def generate_test_query_params() -> dict:
    """Provides a dict of default query params to be used for API tests"""
    return {
        "model": "N",
        "year": "2023",
        "zip": "90210",
        "radius": "500",
    }


def program_vcr():
    # Use path relative to the project root
    cassette_library_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "tests", "cassettes"
    )
    _vcr = vcr.VCR(
        cassette_library_dir=cassette_library_dir,
        record_mode="new_episodes",
    )

    return _vcr


def mock_gcp_error_reporting():
    """Mock Google Cloud Error Reporting client for testing without GCP credentials.

    Returns:
        Mock: A mocked error_reporting module with Client class
    """
    mock_error_reporting = Mock()
    mock_client = MagicMock()
    mock_http_context = MagicMock()

    # Mock the Client class
    mock_error_reporting.Client.return_value = mock_client
    mock_error_reporting.HTTPContext = mock_http_context

    # Mock the report method to succeed silently
    mock_client.report.return_value = None

    return mock_error_reporting


def mock_gcp_metadata_server():
    """Mock GCP metadata server responses for health check tests.

    Returns:
        dict: Mock response simulating GCP metadata server
    """
    return {
        "instance": {
            "id": "test-instance-id",
            "zone": "projects/test-project/zones/us-central1-a",
        }
    }


def get_common_test_headers(user_agent: str = "TestClient/1.0") -> dict:
    """Generate common HTTP headers for API tests.

    Args:
        user_agent (str): User agent string for the test client

    Returns:
        dict: HTTP headers dictionary
    """
    return {"User-Agent": user_agent}
