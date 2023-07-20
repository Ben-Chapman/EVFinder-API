import httpx

from src.libs.libs import async_timeit
from src.routers.logger import send_error_to_gcp


class AsyncHTTPClient:
    def __init__(
        self,
        base_url: str,
        timeout_value: int,
        use_http2: bool = True,
        verify: bool = True,
    ):
        self.base_url = base_url
        self.timeout_value = timeout_value
        self.verify = verify

        timeouts = httpx.Timeout(10.0, read=self.timeout_value)
        self.client = httpx.AsyncClient(
            http2=use_http2,
            base_url=base_url,
            timeout=timeouts,
            verify=verify,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        await self.client.aclose()

    @async_timeit
    async def get(self, uri: str, headers: dict, params: dict | None = None):
        print(headers)
        try:
            resp = await self.client.get(uri, headers=headers, params=params)
            resp.raise_for_status()

        except httpx.TimeoutException as e:
            error_message = f"The request to {e.request.url!r} timed out. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "504",
                },
            )
            return error_message

        except httpx.NetworkError as e:
            error_message = f"A network error occurred for {e.request.url!r}. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "503",
                },
            )
            return error_message

        except httpx.DecodingError as e:
            error_message = f"""Decoding of the response to {e.request.url!r} failed,
                due to a malformed encoding. {e}."""
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "400",
                },
            )
            return error_message

        except httpx.TooManyRedirects as e:
            error_message = f"Too many redirects for {e.request.url!r} failed. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "429",
                },
            )
            return error_message

        except httpx.RemoteProtocolError as e:
            error_message = f"An error occurred while requesting {e.request.url!r}. {e}"
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "400",
                },
            )
            return error_message

        # Base exceptions to catch all remaining errors
        except httpx.HTTPStatusError as e:
            error_message = f"""Error response {e.response.status_code} while requesting
            {e.request.url!r}."""
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "500",
                },
            )
            return error_message

        except httpx.RequestError as e:
            error_message = f"An error occurred while requesting {e.request.url!r}. {e}"
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "400",
                },
            )
            return error_message

        else:
            return resp

    @async_timeit
    async def post(self, uri: str, headers: dict, post_data: dict):
        try:
            resp = await self.client.post(uri, headers=headers, json=post_data)
            resp.raise_for_status()

        except httpx.TimeoutException as e:
            error_message = f"The request to {e.request.url!r} timed out. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "504",
                },
            )
            return error_message

        except httpx.NetworkError as e:
            error_message = f"A network error occurred for {e.request.url!r}. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "503",
                },
            )
            return error_message

        except httpx.DecodingError as e:
            error_message = f"""Decoding of the response to {e.request.url!r} failed,
                due to a malformed encoding. {e}."""
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "400",
                },
            )
            return error_message

        except httpx.TooManyRedirects as e:
            error_message = f"Too many redirects for {e.request.url!r} failed. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "429",
                },
            )
            return error_message

        # Base exceptions to catch all remaining errors
        except httpx.HTTPStatusError as e:
            error_message = f"""Error response {e.response.status_code} while requesting
            {e.request.url!r}."""
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "500",
                },
            )
            return error_message

        except httpx.RequestError as e:
            error_message = f"An error occurred while requesting {e.request.url!r}. {e}"
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers["User-Agent"],
                    "status_code": "400",
                },
            )
            return error_message

        else:
            return resp
