from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.routers.logger import ErrorMessage, send_error_to_gcp

client = TestClient(app)


def test_accept_application_error_endpoint():
    """Test the /api/logger/error POST endpoint accepts error messages"""
    error_data = {
        "errorMessage": "Test error message",
        "userAgent": "Mozilla/5.0 Test Browser",
        "appVersion": "1.0.0",
    }

    response = client.post("/api/logger/error", json=error_data)

    assert response.status_code == 202, (
        f"Expected 202 status, got {response.status_code}"
    )
    assert response.json() == {"status": "OK"}


def test_accept_application_error_with_special_characters():
    """Test error logging with special characters"""
    error_data = {
        "errorMessage": "Error with special chars: <>&\"'",
        "userAgent": "Test/1.0",
        "appVersion": "2.0.0",
    }

    response = client.post("/api/logger/error", json=error_data)

    assert response.status_code == 202
    assert response.json() == {"status": "OK"}


def test_accept_application_error_with_long_message():
    """Test error logging with very long message"""
    error_data = {
        "errorMessage": "x" * 10000,  # Very long error message
        "userAgent": "Test/1.0",
        "appVersion": "1.0.0",
    }

    response = client.post("/api/logger/error", json=error_data)

    assert response.status_code == 202
    assert response.json() == {"status": "OK"}


def test_accept_application_error_missing_fields():
    """Test error logging with missing fields"""
    error_data = {
        "errorMessage": "Test error"
        # Missing userAgent and appVersion
    }

    response = client.post("/api/logger/error", json=error_data)

    # Should return validation error
    assert response.status_code == 422


def test_send_error_to_gcp_with_error_message_object(mock_gcp_error_reporting):
    """Test send_error_to_gcp with ErrorMessage object"""
    # The mock is provided by the conftest fixture
    # Setup mock client
    mock_client = Mock()
    mock_gcp_error_reporting.Client.return_value = mock_client

    # Create ErrorMessage object
    error = ErrorMessage(
        errorMessage="Test error from frontend",
        userAgent="Mozilla/5.0",
        appVersion="1.0.0",
    )

    # Call the function
    send_error_to_gcp(error)

    # Verify Client was instantiated with version
    mock_gcp_error_reporting.Client.assert_called_once_with(version="1.0.0")

    # Verify HTTPContext was created
    mock_gcp_error_reporting.HTTPContext.assert_called_once()

    # Verify report was called
    mock_client.report.assert_called_once()


def test_send_error_to_gcp_with_string_error(mock_gcp_error_reporting):
    """Test send_error_to_gcp with string error and http_context"""
    # Setup mock
    mock_client = Mock()
    mock_gcp_error_reporting.Client.return_value = mock_client

    # Call with string error
    http_context = {
        "method": "GET",
        "url": "https://example.com/test",
        "user_agent": "TestAgent/1.0",
        "status_code": "500",
    }

    send_error_to_gcp("Test error string", http_context=http_context)

    # Verify Client was instantiated without version
    mock_gcp_error_reporting.Client.assert_called_once_with()

    # Verify HTTPContext was created with correct params
    mock_gcp_error_reporting.HTTPContext.assert_called_once_with(
        method="GET",
        url="https://example.com/test",
        user_agent="TestAgent/1.0",
        response_status_code="500",
    )

    # Verify report was called
    mock_client.report.assert_called_once()


def test_send_error_to_gcp_handles_exceptions(mock_gcp_error_reporting):
    """Test send_error_to_gcp handles exceptions gracefully"""
    # Setup mock to raise exception
    mock_client = Mock()
    mock_client.report.side_effect = Exception("GCP API Error")
    mock_gcp_error_reporting.Client.return_value = mock_client

    error = ErrorMessage(
        errorMessage="Test error", userAgent="Mozilla/5.0", appVersion="1.0.0"
    )

    # Should not raise exception
    try:
        send_error_to_gcp(error)
    except Exception as e:
        pytest.fail(f"send_error_to_gcp raised exception: {e}")


def test_send_error_to_gcp_with_none_http_context(mock_gcp_error_reporting):
    """Test send_error_to_gcp with None http_context"""
    # Setup mock
    mock_client = Mock()
    mock_gcp_error_reporting.Client.return_value = mock_client

    error = ErrorMessage(
        errorMessage="Test error", userAgent="Mozilla/5.0", appVersion="1.0.0"
    )

    # Should handle None http_context
    send_error_to_gcp(error, http_context=None)

    # Verify report was called
    mock_client.report.assert_called_once()


def test_error_message_model_validation():
    """Test ErrorMessage Pydantic model validation"""
    # Valid error message
    error = ErrorMessage(
        errorMessage="Test", userAgent="Mozilla/5.0", appVersion="1.0.0"
    )

    assert error.errorMessage == "Test"
    assert error.userAgent == "Mozilla/5.0"
    assert error.appVersion == "1.0.0"


def test_error_message_model_missing_fields():
    """Test ErrorMessage validation with missing fields"""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ErrorMessage(errorMessage="Test")


def test_accept_application_error_invalid_json():
    """Test error logging endpoint with invalid JSON"""
    response = client.post(
        "/api/logger/error",
        data="not valid json",
        headers={"Content-Type": "application/json"},
    )

    # Should return 422 validation error
    assert response.status_code == 422


def test_accept_application_error_empty_strings():
    """Test error logging with empty strings"""
    error_data = {"errorMessage": "", "userAgent": "", "appVersion": ""}

    response = client.post("/api/logger/error", json=error_data)

    # Should accept empty strings
    assert response.status_code == 202
    assert response.json() == {"status": "OK"}


def test_send_error_to_gcp_multiple_calls(mock_gcp_error_reporting):
    """Test multiple calls to send_error_to_gcp"""
    # Setup mock
    mock_client = Mock()
    mock_gcp_error_reporting.Client.return_value = mock_client

    # Make multiple calls
    for i in range(5):
        error = ErrorMessage(
            errorMessage=f"Error {i}", userAgent="Test", appVersion="1.0"
        )
        send_error_to_gcp(error)

    # Verify Client was called 5 times
    assert mock_gcp_error_reporting.Client.call_count == 5
    assert mock_client.report.call_count == 5


def test_send_error_to_gcp_with_unicode(mock_gcp_error_reporting):
    """Test error logging with unicode characters"""
    # Setup mock
    mock_client = Mock()
    mock_gcp_error_reporting.Client.return_value = mock_client

    error = ErrorMessage(
        errorMessage="Error with unicode: 你好 🚗",
        userAgent="Mozilla/5.0",
        appVersion="1.0.0",
    )

    send_error_to_gcp(error)

    # Verify it was called without errors
    mock_client.report.assert_called_once()
