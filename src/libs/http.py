import httpx

from tenacity import (
    RetryError,
    retry,
    stop_after_delay,
    stop_after_attempt,
    wait_random,
    retry_if_exception_type,
)

from libs.libs import async_timeit


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
    @retry(
        stop=(stop_after_delay(15) | stop_after_attempt(5)),
        wait=wait_random(min=1, max=3),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def get(self, uri: str, headers: dict, params: dict | None = None):
        try:
            return await self.client.get(uri, headers=headers, params=params)
        except RetryError as e:
            return e

    @async_timeit
    @retry(
        stop=(stop_after_delay(15) | stop_after_attempt(5)),
        wait=wait_random(min=1, max=3),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def post(self, uri: str, headers: dict, post_data: dict):
        try:
            return await self.client.post(uri, headers=headers, json=post_data)
        except RetryError as e:
            return e
