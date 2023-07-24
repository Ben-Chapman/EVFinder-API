import asyncio
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

    async def get(
        self, uri: str | list, headers: dict | None = None, params: dict | None = None
    ):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = None

        if loop and loop.is_running():
            print(
                "Async event loop already running. Adding coroutine to the event loop."
            )

            result = loop.create_task(
                self.gather_urls_for_asyncio(uri, headers, params)
            )
        else:
            print("Starting new event loop")
            result = asyncio.run(self.gather_urls_for_asyncio(uri, headers, params))

        foo = await result
        print(f"\n\n\nLoop result: {foo[0].json()}\n\n\n")
        return foo[0]

    async def gather_urls_for_asyncio(
        self, uri: str | list, headers: dict | None = None, params: dict | None = None
    ):
        tasks = []

        if type(uri) == str:
            if headers or params:
                tasks.append(
                    self.fetch_api_data(uri=uri, headers=headers, params=params)
                )
                # print(f"\n\n\nTasks: {tasks}\n\n\n")
        else:
            for url in uri:
                tasks.append(
                    self.fetch_api_data(uri=url[0], headers=url[1], params=url[2])
                )

        return await asyncio.gather(*tasks)

    @async_timeit
    async def fetch_api_data(self, uri: str, headers: dict, params: dict | None = None):
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
            print(f"Resp here: {resp.json()}")
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
