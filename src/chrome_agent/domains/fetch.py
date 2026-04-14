"""CDP Fetch domain.

A domain for letting clients substitute browser's network layer with client code.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


RequestId = str

# Stages of the request to handle. Request will intercept before the request is
# sent. Response will intercept after the response is received (but before response
# body is received).
RequestStage = str  # Literal enum: "Request", "Response"

RequestPattern = dict  # Object type

# Response HTTP header entry
HeaderEntry = dict  # Object type

# Authorization challenge for HTTP status code 401 or 407.
AuthChallenge = dict  # Object type

# Response to an AuthChallenge.
AuthChallengeResponse = dict  # Object type

class Fetch:
    """A domain for letting clients substitute browser's network layer with client code."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        """Disables the fetch domain."""
        return await self._client.send(method="Fetch.disable")

    async def enable(self, patterns: list[RequestPattern] | None = None, handle_auth_requests: bool | None = None) -> dict:
        """Enables issuing of requestPaused events. A request will be paused until client
calls one of failRequest, fulfillRequest or continueRequest/continueWithAuth.
        """
        params: dict[str, Any] = {}
        if patterns is not None:
            params["patterns"] = patterns
        if handle_auth_requests is not None:
            params["handleAuthRequests"] = handle_auth_requests
        return await self._client.send(method="Fetch.enable", params=params)

    async def fail_request(self, request_id: RequestId, error_reason: str) -> dict:
        """Causes the request to fail with specified reason."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["errorReason"] = error_reason
        return await self._client.send(method="Fetch.failRequest", params=params)

    async def fulfill_request(
        self,
        request_id: RequestId,
        response_code: int,
        response_headers: list[HeaderEntry] | None = None,
        binary_response_headers: str | None = None,
        body: str | None = None,
        response_phrase: str | None = None,
    ) -> dict:
        """Provides response to the request."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["responseCode"] = response_code
        if response_headers is not None:
            params["responseHeaders"] = response_headers
        if binary_response_headers is not None:
            params["binaryResponseHeaders"] = binary_response_headers
        if body is not None:
            params["body"] = body
        if response_phrase is not None:
            params["responsePhrase"] = response_phrase
        return await self._client.send(method="Fetch.fulfillRequest", params=params)

    async def continue_request(
        self,
        request_id: RequestId,
        url: str | None = None,
        method: str | None = None,
        post_data: str | None = None,
        headers: list[HeaderEntry] | None = None,
        intercept_response: bool | None = None,
    ) -> dict:
        """Continues the request, optionally modifying some of its parameters."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        if url is not None:
            params["url"] = url
        if method is not None:
            params["method"] = method
        if post_data is not None:
            params["postData"] = post_data
        if headers is not None:
            params["headers"] = headers
        if intercept_response is not None:
            params["interceptResponse"] = intercept_response
        return await self._client.send(method="Fetch.continueRequest", params=params)

    async def continue_with_auth(self, request_id: RequestId, auth_challenge_response: AuthChallengeResponse) -> dict:
        """Continues a request supplying authChallengeResponse following authRequired event."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["authChallengeResponse"] = auth_challenge_response
        return await self._client.send(method="Fetch.continueWithAuth", params=params)

    async def continue_response(
        self,
        request_id: RequestId,
        response_code: int | None = None,
        response_phrase: str | None = None,
        response_headers: list[HeaderEntry] | None = None,
        binary_response_headers: str | None = None,
    ) -> dict:
        """Continues loading of the paused response, optionally modifying the
response headers. If either responseCode or headers are modified, all of them
must be present.
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        if response_code is not None:
            params["responseCode"] = response_code
        if response_phrase is not None:
            params["responsePhrase"] = response_phrase
        if response_headers is not None:
            params["responseHeaders"] = response_headers
        if binary_response_headers is not None:
            params["binaryResponseHeaders"] = binary_response_headers
        return await self._client.send(method="Fetch.continueResponse", params=params)

    async def get_response_body(self, request_id: RequestId) -> dict:
        """Causes the body of the response to be received from the server and
returned as a single string. May only be issued for a request that
is paused in the Response stage and is mutually exclusive with
takeResponseBodyForInterceptionAsStream. Calling other methods that
affect the request or disabling fetch domain before body is received
results in an undefined behavior.
Note that the response body is not available for redirects. Requests
paused in the _redirect received_ state may be differentiated by
`responseCode` and presence of `location` response header, see
comments to `requestPaused` for details.
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="Fetch.getResponseBody", params=params)

    async def take_response_body_as_stream(self, request_id: RequestId) -> dict:
        """Returns a handle to the stream representing the response body.
The request must be paused in the HeadersReceived stage.
Note that after this command the request can't be continued
as is -- client either needs to cancel it or to provide the
response body.
The stream only supports sequential read, IO.read will fail if the position
is specified.
This method is mutually exclusive with getResponseBody.
Calling other methods that affect the request or disabling fetch
domain before body is received results in an undefined behavior.
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="Fetch.takeResponseBodyAsStream", params=params)
