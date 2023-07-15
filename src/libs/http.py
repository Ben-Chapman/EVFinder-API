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

        self.client = httpx.AsyncClient(
            http2=use_http2,
            base_url=base_url,
            timeout=timeout_value,
            verify=verify,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        await self.client.aclose()

    @async_timeit
    async def get(self, uri: str, headers: dict, params: dict | None = None):
        try:
            resp = await self.client.get(uri, headers=headers, params=params)
            resp.raise_for_status()
            return resp
        except httpx.TimeoutException as e:
            print(f"The request to {e.request.url!r} timed out: {e}.")
            send_error_to_gcp(f"The request to {e.request.url!r} timed out.\n{e}.")

        except httpx.NetworkError as e:
            print(f"Network error to {e.request.url!r}: {e}.")
            send_error_to_gcp(f"A network error occurred for {e.request.url!r}.\n{e}.")

        except httpx.DecodingError as e:
            print(f"Decoding error {e.request.url!r}: {e}.")
            send_error_to_gcp(
                f"""Decoding of the response to {e.request.url!r} failed,
                due to a malformed encoding.\n{e}."""
            )

        except httpx.TooManyRedirects as e:
            print(f"Redirects error {e.request.url!r}: {e}.")
            send_error_to_gcp(f"Too many redirects for {e.request.url!r} failed.\n{e}.")

        except httpx.HTTPStatusError as e:
            print(f"\n\n\nHTTP helper error here.\n\n\n{e}")
            send_error_to_gcp(
                f"Error response {e.response.status_code} while requesting {e.request.url!r}."
            )

        except httpx.RequestError as e:
            send_error_to_gcp(f"An error occurred while requesting {e.request.url!r}.")

    @async_timeit
    async def post(self, uri: str, headers: dict, post_data: dict):
        try:
            return await self.client.post(uri, headers=headers, json=post_data)
        except Exception as e:
            return e
