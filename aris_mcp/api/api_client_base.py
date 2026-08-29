"""Shared HTTP base client for the ARIS API wrapper."""

from typing import Any
from urllib.parse import urljoin

import requests
import urllib3


def _resolve_request_url(base_url: str, endpoint: str) -> str:
    if endpoint.startswith("http"):
        return endpoint
    return urljoin(base_url, endpoint.lstrip("/"))


def _build_request_headers(
    content_type: str | None, accept: str | None, headers: dict[str, str] | None
) -> dict[str, str]:
    req_headers: dict[str, str] = {}
    if content_type:
        req_headers["Content-Type"] = content_type
    if accept:
        req_headers["Accept"] = accept
    if headers:
        req_headers.update(headers)
    return req_headers


def _parse_response_body(response: requests.Response) -> Any:
    """Return parsed JSON, or a text/success fallback dict."""
    if response.status_code == 204 or not response.text.strip():
        return {"status": "success"}

    ctype = response.headers.get("Content-Type", "")
    if "json" in ctype:
        try:
            return response.json()
        except Exception:
            pass
    return {"status": "success", "text": response.text}


class ApiClientBase:
    """Thin ``requests.Session`` wrapper with token / basic-auth support.

    ARIS speaks JSON over its REST API. Auth is either an OAuth2 bearer token
    (resolved by :mod:`aris_mcp.auth`) or HTTP basic. Callers pass an explicit
    ``accept``/``content_type`` so this base never forces a content type on a
    payload that needs otherwise.
    """

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify: bool = True,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.username = username
        self.password = password
        self._session = requests.Session()
        self._session.verify = verify

        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
        elif username and password:
            self._session.auth = (username, password)

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        content_type: str | None = None,
        accept: str | None = "application/json",
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Perform an HTTP request and return parsed JSON, or raw text.

        Returns a dict/list when the response is JSON, otherwise
        ``{"status": "success", "text": <body>}``. Raises on HTTP >= 400.
        """
        url = _resolve_request_url(self.base_url, endpoint)
        req_headers = _build_request_headers(content_type, accept, headers)

        response = self._session.request(
            method=method,
            url=url,
            headers=req_headers or None,
            params=params,
            data=data,
            json=json,
        )

        if response.status_code >= 400:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        return _parse_response_body(response)
