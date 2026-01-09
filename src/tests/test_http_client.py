import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.libs.http import AsyncHTTPClient


@pytest.mark.asyncio
async def test_http_client_initialization():
    """Test AsyncHTTPClient initialization with default parameters"""
    client = AsyncHTTPClient(base_url="https://example.com", timeout_value=10.0)

    assert client.base_url == "https://example.com"
    assert client.timeout_value == 10.0
    assert client.verify is True
    assert client.client is not None

    await client.close()


@pytest.mark.asyncio
async def test_http_client_context_manager():
    """Test AsyncHTTPClient as context manager"""
    async with AsyncHTTPClient(
        base_url="https://example.com", timeout_value=10.0
    ) as client:
        assert client.client is not None
        assert client.base_url == "https://example.com"


@pytest.mark.asyncio
async def test_http_client_with_http2_disabled():
    """Test AsyncHTTPClient with HTTP/2 disabled"""
    client = AsyncHTTPClient(
        base_url="https://example.com", timeout_value=10.0, use_http2=False
    )

    assert client.client is not None
    await client.close()


@pytest.mark.asyncio
async def test_http_client_with_ssl_verification_disabled():
    """Test AsyncHTTPClient with SSL verification disabled"""
    client = AsyncHTTPClient(
        base_url="https://example.com", timeout_value=10.0, verify=False
    )

    assert client.verify is False
    await client.close()


@pytest.mark.asyncio
async def test_http_get_single_url_success():
    """Test successful GET request to single URL"""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            mock_response.raise_for_status = Mock()
            result = await client.get("/test", headers={}, params={})

            assert result.status_code == 200
            assert result.json() == {"data": "test"}


@pytest.mark.asyncio
async def test_http_get_multiple_urls():
    """Test GET request to multiple URLs concurrently"""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            mock_response.raise_for_status = Mock()

            urls = [
                ["/url1", {}, {}],
                ["/url2", {}, {}],
            ]
            results = await client.get(urls)

            assert isinstance(results, list)
            assert len(results) == 2


@pytest.mark.asyncio
async def test_http_post_success():
    """Test successful POST request"""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "posted"}

    with patch.object(
        httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            mock_response.raise_for_status = Mock()
            result = await client.post("/test", headers={}, post_data={"key": "value"})

            assert result.status_code == 200


@pytest.mark.asyncio
@patch("src.routers.logger.send_error_to_gcp")
async def test_http_timeout_exception(mock_send_error):
    """Test handling of timeout exception"""
    mock_request = Mock()
    mock_request.url = "https://example.com/test"
    mock_request.method = "GET"

    timeout_error = httpx.TimeoutException("Timeout", request=mock_request)

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=timeout_error
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            result = await client.get("/test", headers={"User-Agent": "Test"})

            # Should return error response dict
            assert isinstance(result, dict)
            assert "errorMessage" in result


@pytest.mark.asyncio
@patch("src.routers.logger.send_error_to_gcp")
async def test_http_network_error(mock_send_error):
    """Test handling of network error"""
    mock_request = Mock()
    mock_request.url = "https://example.com/test"
    mock_request.method = "GET"

    network_error = httpx.NetworkError("Network error", request=mock_request)

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=network_error
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            result = await client.get("/test", headers={"User-Agent": "Test"})

            assert isinstance(result, dict)
            assert "errorMessage" in result


@pytest.mark.asyncio
@patch("src.routers.logger.send_error_to_gcp")
async def test_http_decoding_error(mock_send_error):
    """Test handling of decoding error"""
    mock_request = Mock()
    mock_request.url = "https://example.com/test"
    mock_request.method = "GET"

    decoding_error = httpx.DecodingError("Decoding failed", request=mock_request)

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=decoding_error
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            result = await client.get("/test", headers={"User-Agent": "Test"})

            assert isinstance(result, dict)
            assert "errorMessage" in result


@pytest.mark.asyncio
@patch("src.routers.logger.send_error_to_gcp")
async def test_http_too_many_redirects(mock_send_error):
    """Test handling of too many redirects"""
    mock_request = Mock()
    mock_request.url = "https://example.com/test"
    mock_request.method = "GET"

    redirect_error = httpx.TooManyRedirects("Too many redirects", request=mock_request)

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=redirect_error
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            result = await client.get("/test", headers={"User-Agent": "Test"})

            assert isinstance(result, dict)
            assert "errorMessage" in result


@pytest.mark.asyncio
@patch("src.routers.logger.send_error_to_gcp")
async def test_http_remote_protocol_error(mock_send_error):
    """Test handling of remote protocol error"""
    mock_request = Mock()
    mock_request.url = "https://example.com/test"
    mock_request.method = "GET"

    protocol_error = httpx.RemoteProtocolError("Protocol error", request=mock_request)

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=protocol_error
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            result = await client.get("/test", headers={"User-Agent": "Test"})

            assert isinstance(result, dict)
            assert "errorMessage" in result


@pytest.mark.asyncio
@patch("src.routers.logger.send_error_to_gcp")
async def test_http_status_error(mock_send_error):
    """Test handling of HTTP status error"""
    mock_request = Mock()
    mock_request.url = "https://example.com/test"
    mock_request.method = "GET"

    mock_response = Mock()
    mock_response.status_code = 500

    status_error = httpx.HTTPStatusError(
        "Server error", request=mock_request, response=mock_response
    )

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=status_error
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            result = await client.get("/test", headers={"User-Agent": "Test"})

            assert isinstance(result, dict)
            assert "errorMessage" in result


@pytest.mark.asyncio
@patch("src.routers.logger.send_error_to_gcp")
async def test_http_request_error(mock_send_error):
    """Test handling of generic request error"""
    mock_request = Mock()
    mock_request.url = "https://example.com/test"
    mock_request.method = "GET"

    request_error = httpx.RequestError("Request failed", request=mock_request)

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=request_error
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            result = await client.get("/test", headers={"User-Agent": "Test"})

            assert isinstance(result, dict)
            assert "errorMessage" in result


@pytest.mark.asyncio
async def test_http_post_multiple_urls():
    """Test POST request to multiple URLs concurrently"""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch.object(
        httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            mock_response.raise_for_status = Mock()

            urls = [
                ["/url1", {}, {"data": 1}],
                ["/url2", {}, {"data": 2}],
            ]
            results = await client.post(urls)

            assert isinstance(results, list)
            assert len(results) == 2


@pytest.mark.asyncio
async def test_http_gather_urls_single():
    """Test gather_urls_for_asyncio with single URL"""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch.object(
        httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        async with AsyncHTTPClient(
            base_url="https://example.com", timeout_value=10.0
        ) as client:
            mock_response.raise_for_status = Mock()
            results = await client.gather_urls_for_asyncio(
                uri="/test", headers={}, params={}, method="get"
            )

            assert isinstance(results, list)
            assert len(results) == 1


@pytest.mark.asyncio
async def test_http_timeout_configuration():
    """Test that timeout configuration is properly set"""
    client = AsyncHTTPClient(base_url="https://example.com", timeout_value=30.5)

    # Verify the client has timeout configured
    assert client.timeout_value == 30.5
    await client.close()
