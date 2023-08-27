# Copyright 2023 Ben Chapman
#
# This file is part of The EV Finder.
#
# The EV Finder is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# The EV Finder is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with The EV Finder.
# If not, see <https://www.gnu.org/licenses/>.

import asyncio
import time

import httpx
from src.libs.libs import async_timeit
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
        """A HTTP helper library to be used to fetch manufacturer inventory. This library
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
        print(
            f"Transaction for {self.base_url} took {end_time - self.start_time} seconds."
        )
        await self.client.aclose()

    async def close(self):
        await self.client.aclose()

    async def execute_requests(
        self,
        http_request_method: str,
        uri: str | list,
        headers: dict | None = None,
        params: dict | None = None,
        post_data: dict | None = None,
    ) -> list | httpx.Response:
        """Wrap the asyncio coroutine into a Task and schedule its execution.

        Args:
            http_request_method (str): Which HTTP request method to use (get or post)
            uri (str | list): A single HTTP URI, or list of HTTP URIs to fetch. If uri
            is a list, it must be in the format of: [uri, headers, params|post_data].

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
                self.gather_urls_for_asyncio(
                    http_request_method=http_request_method,
                    uri=uri,
                    headers=headers,
                    params=params,
                    post_data=post_data,
                )
            )
        else:
            # If for some reason we don't have a running event loop, start one
            result = asyncio.run(
                self.gather_urls_for_asyncio(
                    http_request_method=http_request_method,
                    uri=uri,
                    headers=headers,
                    params=params,
                    post_data=post_data,
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
        http_request_method: str,
        uri: str | list,
        headers: dict | None = None,
        params: dict | None = None,
        post_data: dict | None = None,
    ):
        """Create a list of tasks required for asyncio to run. These tasks are httpx
        request futures.

        Args:
            http_request_method (str): Which HTTP request method to use (get or post)
            uri (str | list): A single HTTP URI, or list of HTTP URIs to fetch. If uri
            is a list, it must be in the format of: [uri, headers, params|post_data].

            headers (dict | None, optional): HTTP headers to include with this request.
            Defaults to None.

            params (dict | None, optional): HTTP query parameters to include with this request.
            Defaults to None.

        Returns:
            list: An aggregate list of returned values from the HTTPX request.
        """
        tasks = []

        if type(uri) is str:
            if headers or params:
                tasks.append(
                    self.fetch_api_data(
                        http_request_method=http_request_method,
                        uri=uri,
                        headers=headers,
                        params=params,
                        post_data=post_data,
                    )
                )
        else:
            for url in uri:
                if http_request_method.lower() == "get":
                    tasks.append(
                        self.fetch_api_data(
                            http_request_method=http_request_method,
                            uri=url[0],
                            headers=url[1],
                            params=url[2],
                        )
                    )
                elif http_request_method.lower() == "post":
                    tasks.append(
                        self.fetch_api_data(
                            http_request_method=http_request_method,
                            uri=url[0],
                            headers=url[1],
                            post_data=url[2],
                        )
                    )

        return await asyncio.gather(*tasks)

    async def fetch_api_data(
        self,
        http_request_method: str,
        uri: str,
        headers: dict,
        params: dict | None = None,
        post_data: dict | None = None,
    ) -> dict:
        """Helper function to issue API requests through HTTPX

        Args:
            http_request_method (str): Which HTTP request method to use (GET or POST)
            uri (str): A HTTP URI to fetch
            headers (dict): HTTP headers to include with this request.
            params (dict | None, optional): HTTP query parameters to include with this request.
            Defaults to None.
            post_data (dict | None, optional): Request body to be included with a HTTP
            POST request to the specified API. Defaults to None.

        Returns:
            ResponseObject: The HTTP response from the requested URL.
        """

        error_message = "An error occurred obtaining vehicle inventory for this search."

        try:
            if http_request_method.lower() == "get":
                resp = await self.client.get(uri, headers=headers, params=params)
            elif http_request_method.lower() == ("post"):
                resp = await self.client.post(uri, headers=headers, json=post_data)
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

    @async_timeit
    async def get(self, uri: str, headers: dict, params: dict) -> httpx.Response:
        """Perform an HTTP GET request for a given URL

        Args:
            uri (str): The URI to which this request will be made
            headers (dict): HTTP headers to include with this request
            params (dict): HTTP query parameters to include with this request.

        Returns:
            httpx.Response: An HTTPX response for this request.
        """
        return await self.execute_requests(
            http_request_method="GET", uri=uri, headers=headers, params=params
        )

    @async_timeit
    async def post(
        self,
        uri: str | list,
        headers: dict | None = None,
        post_data: dict | None = None,
    ) -> httpx.Response:
        """Perform an HTTP POST request for a given URL

        Args:
            uri (str): The URI to which this request will be made
            headers (dict): HTTP headers to include with this request
            post_data (dict): Request body to be included with this request

        Returns:
            httpx.Response: An HTTPX response for this request.
        """
        return await self.execute_requests(
            http_request_method="POST", uri=uri, headers=headers, post_data=post_data
        )
