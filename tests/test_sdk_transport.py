"""Capabilities through the SDK (CONN-ARIS-MCP-SDK-CENTRALIZATION-R001)."""

from __future__ import annotations

import json
import pathlib
import re

import httpx
import pytest
from scion_sdk.auth.static import BearerAuth

from aris_mcp.api.api_client_aris import ArisApi

ID = "CONN-ARIS-MCP-SDK-CENTRALIZATION-R001"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def _with_transport(api: ArisApi, handler) -> ArisApi:
    api._session = httpx.Client(
        transport=httpx.MockTransport(handler), auth=api._session.auth
    )
    return api


@pytest.mark.spec(f"{ID}.1")
def test_client_is_governed_and_sends_bearer_auth() -> None:
    for path in (ROOT / "aris_mcp").rglob("*.py"):
        assert not re.search(r"^\s*(import|from) requests\b", path.read_text(), re.M)
    api = ArisApi(base_url="http://aris.test/abs/api", token="tok")
    assert isinstance(api._session, httpx.Client)
    assert isinstance(api._session.auth, BearerAuth)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": []})

    _with_transport(api, handler).list_models()
    assert seen[0].headers["Authorization"] == "Bearer tok"
    basic = ArisApi(base_url="http://aris.test", username="u", password="p")
    assert isinstance(basic._session.auth, httpx.BasicAuth)


@pytest.mark.spec(f"{ID}.3")
def test_request_shapes_are_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARIS_ENABLE_WRITE", "true")
    api = ArisApi(base_url="http://aris.test/abs/api", token="tok")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "PUT":
            return httpx.Response(204)
        return httpx.Response(500, text="boom")

    _with_transport(api, handler)
    api.set_model_attributes("M1", {"k": "v"})
    assert seen[0].method == "PUT"
    assert str(seen[0].url) == "http://aris.test/abs/api/models/M1/attributes"
    assert json.loads(seen[0].content) == {"attributes": {"k": "v"}}
    with pytest.raises(Exception, match=r"API error: 500 - boom"):
        api.list_models()


@pytest.mark.spec(f"{ID}.4")
def test_dependencies_come_from_the_sdk() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert not re.search(r'"requests\s*[>=<~!]', text)
    floors = re.findall(r"scion-sdk\[mcp\]>=(\d+)\.(\d+)\.(\d+)", text)
    assert floors and all(tuple(map(int, f)) >= (0, 3, 11) for f in floors)
