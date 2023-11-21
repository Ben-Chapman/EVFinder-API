import asyncio
import time
from typing import Literal

import httpx

from src.libs.responses import error_response
from src.routers.logger import send_error_to_gcp


class AsyncHTTPClient:
    def __init__(
        self,
        base_url: str,
        timeout_value: float,
        use_http2: bool = True,
        verify: bool = True,
    ):
        """A HTTP helper library used to fetch manufacturer inventory. This library
        is designed to be called directly or used as a context manager and is async
        compatible.

        Args:
            base_url (str): A URL to use as the base when building request URLs.
            timeout_value (float): How long to wait for an HTTP response. Accepts float
            values like 5.0 or 30.5.
            use_http2 (bool, optional): Use HTTP/2 for requests? If HTTP/2 is not supported
            by the destination host, falls back to HTTP/1.1. Defaults to True.
            verify (bool, optional): Verify SSL certificates? If True and a certificate
            can not be verified, will fail. Defaults to True.
        """
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

        self.start_time = time.perf_counter()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        end_time = time.perf_counter()
        print(f"{end_time - self.start_time} sec - {self.base_url}")
        await self.client.aclose()

    async def close(self):
        await self.client.aclose()

    async def get(
        self, uri: str | list, headers: dict | None = None, params: dict | None = None
    ) -> list | httpx.Response:
        """Wrap the asyncio coroutine into a Task and schedule its execution.

        Args:
            uri (str | list): A single HTTP URI, or list of HTTP URIs to fetch. If uri
            is a list, it must be in the format of: [uri, headers, params].

            headers (dict | None, optional): HTTP headers to include with this request.
            Defaults to None.

            params (dict | None, optional): HTTP query parameters to include with this request.
            Defaults to None.

        Returns:
            (list | httpx.Response): The result of an asyncio Task object.
            If multiple URLs were fetched, returns a list of httpx.Responses. If a single
            URL was fetched returns a single httpx.Response.
        """

        # Make sure we have a running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = None

        if loop and loop.is_running():
            result = loop.create_task(
                self.gather_urls_for_asyncio(uri, headers, params, method="get")
            )
        else:
            # If for some reason we don't have a running event loop, start one
            result = asyncio.run(
                self.gather_urls_for_asyncio(uri, headers, params, method="get")
            )

        results = await result

        # If the length of the results list is 1, this is likely the result of a single
        # HTTP request. So returning just that done result, not a list containing one item.
        # If the length is > 1, return the list containing the httpx.Responses.
        # TODO: Return all results as a list. Will need to refactor all manufacturer
        # routers.
        if len(results) == 1:
            return results[0]
        else:
            return results

    async def post(
        self,
        uri: str | list,
        headers: dict | None = None,
        post_data: dict | None = None,
    ) -> list | httpx.Response:
        """Wrap the asyncio coroutine into a Task and schedule its execution.

        Args:
            uri (str | list): A single HTTP URI, or list of HTTP URIs to fetch. If uri
            is a list, it must be in the format of: [uri, headers, params].

            headers (dict | None, optional): HTTP headers to include with this request.
            Defaults to None.

            post_data (dict | None, optional): HTTP POST data to include with this request.
            Defaults to None.

        Returns:
            (list | httpx.Response): The result of an asyncio Task object.
            If multiple URLs were fetched, returns a list of httpx.Responses. If a single
            URL was fetched returns a single httpx.Response.
        """
        # Make sure we have a running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = None

        if loop and loop.is_running():
            result = loop.create_task(
                self.gather_urls_for_asyncio(
                    uri=uri, headers=headers, params=post_data, method="post"
                )
            )
        else:
            # If for some reason we don't have a running event loop, start one
            result = asyncio.run(
                self.gather_urls_for_asyncio(
                    uri=uri, headers=headers, params=post_data, method="post"
                )
            )

        results = await result

        # If the length of the results list is 1, this is likely the result of a single
        # HTTP request. So returning just that one result, not a list containing one item.
        # If the length is > 1, return the list containing the httpx.Responses.
        # TODO: Return all results as a list. Will need to refactor all manufacturer
        # routers.
        if len(results) == 1:
            return results[0]
        else:
            return results

    async def gather_urls_for_asyncio(
        self,
        uri: str | list,
        headers: dict | None = None,
        params: dict | None = None,
        method: Literal["get", "post"] = "get",
    ):
        """Create a list of tasks required for asyncio to run. These tasks are httpx
        request futures.

        Args:
            uri (str | list): A single HTTP URI, or list of HTTP URIs to fetch. If uri
            is a list, it must be in the format of: [uri, headers, params].

            headers (dict | None, optional): HTTP headers to include with this request.
            Defaults to None.

            params (dict | None, optional): HTTP query parameters or an HTTP POST body
            to include with this request.
            Defaults to None.

            method (str): Which HTTP method to use for this request. get and post are accepted.

        Returns:
            list: An aggregate list of returned values from the HTTPX request.
        """
        tasks = []

        # If we have a single URL to fetch
        if type(uri) is str:
            if headers or params:
                tasks.append(
                    self.fetch_api_data(
                        uri=uri, headers=headers, params=params, method=method
                    )
                )
        else:
            # If we have multiple URLs to fetch. Add each to the task queue
            for url in uri:
                tasks.append(
                    self.fetch_api_data(
                        uri=url[0], headers=url[1], params=url[2], method=method
                    )
                )

        return await asyncio.gather(*tasks)

    async def fetch_api_data(
        self,
        uri: str,
        headers: dict,
        params: dict | None = None,
        method: Literal["get", "post"] = "get",
    ) -> dict:
        """Helper function to issue API requests through HTTPX

        Args:
            uri (str): A HTTP URI to fetch

            headers (dict): HTTP headers to include with this request.

            params (dict | None, optional): HTTP query parameters or an HTTP POST body
            to include with this request.
            Defaults to None

            method (str): Which HTTP method to use for this request. get and post are accepted.

        Returns:
            ResponseObject: The HTTP response from the requested URL.
        """

        error_message = "An error occurred obtaining vehicle inventory for this search."

        try:
            if method == "get":
                resp = await self.client.get(url=uri, headers=headers, params=params)
            elif method == "post":
                resp = await self.client.post(url=uri, headers=headers, json=params)
            resp.raise_for_status()

        except (httpx.TimeoutException, httpx.ReadTimeout) as e:
            error_data = f"The request to {e.request.url!r} timed out."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers.get("User-Agent") if headers else "",
                    "status_code": "504",
                },
            )
            return error_response(error_message=error_message, error_data=error_data)

        except httpx.NetworkError as e:
            error_data = f"A network error occurred for {e.request.url!r}. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers.get("User-Agent"),
                    "status_code": "503",
                },
            )
            return error_response(error_message=error_message, error_data=error_data)

        except httpx.DecodingError as e:
            error_data = f"""Decoding of the response to {e.request.url!r} failed,
                due to a malformed encoding. {e}."""
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers.get("User-Agent"),
                    "status_code": "400",
                },
            )
            return error_response(error_message=error_message, error_data=error_data)

        except httpx.TooManyRedirects as e:
            error_data = f"Too many redirects for {e.request.url!r} failed. {e}."
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers.get("User-Agent"),
                    "status_code": "429",
                },
            )
            return error_response(error_message=error_message, error_data=error_data)

        except httpx.RemoteProtocolError as e:
            error_data = f"An error occurred while requesting {e.request.url!r}. {e}"
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers.get("User-Agent"),
                    "status_code": "400",
                },
            )
            return error_response(error_message=error_message, error_data=error_data)

        # Base exceptions to catch all remaining errors
        except httpx.HTTPStatusError as e:
            error_data = f"""Error response {e.response.status_code} while requesting
            {e.request.url!r}."""
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers.get("User-Agent"),
                    "status_code": "500",
                },
            )
            return error_response(error_message=error_message, error_data=error_data)

        except httpx.RequestError as e:
            error_data = f"An error occurred while requesting {e.request.url!r}. {e}"
            send_error_to_gcp(
                error_message,
                http_context={
                    "method": e.request.method,
                    "url": str(e.request.url),
                    "user_agent": headers.get("User-Agent"),
                    "status_code": "400",
                },
            )
            return error_response(error_message=error_message, error_data=error_data)

        else:
            return resp
