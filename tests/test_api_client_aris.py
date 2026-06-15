"""Unit tests for the ARIS REST client (endpoint paths + auth + write gate)."""

from __future__ import annotations

from typing import Any

import pytest

from aris_mcp.api.api_client_aris import ArisApi


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200):
        self._payload = payload
        self.status_code = status
        self.headers = {"Content-Type": "application/json"}
        self.text = "x"

    def json(self) -> Any:
        return self._payload


class _RecordingSession:
    """Captures the (method, url) of each request and returns a canned body."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None, Any]] = []
        self.verify = True
        self.headers: dict[str, str] = {}
        self.auth = None

    def request(self, method, url, headers=None, params=None, data=None, json=None):
        self.calls.append((method, url, params, json))
        return _FakeResponse({"items": [{"id": "M1"}]})


@pytest.fixture
def client(monkeypatch) -> ArisApi:
    api = ArisApi(base_url="http://aris.test/abs/api", token="tok")
    session = _RecordingSession()
    monkeypatch.setattr(api, "_session", session)
    return api


def test_list_models_hits_models_path(client: ArisApi):
    client.list_models()
    method, url, _params, _json = client._session.calls[-1]
    assert method == "GET"
    assert url == "http://aris.test/abs/api/models"


def test_model_objects_and_connections_paths(client: ArisApi):
    client.list_model_objects("M1")
    client.list_model_connections("M1")
    urls = [c[1] for c in client._session.calls]
    assert "http://aris.test/abs/api/models/M1/objects" in urls
    assert "http://aris.test/abs/api/models/M1/connections" in urls


def test_set_model_attributes_puts_attributes(client: ArisApi):
    client.set_model_attributes("M1", {"kg_intelligence": "{}"})
    method, url, _params, body = client._session.calls[-1]
    assert method == "PUT"
    assert url == "http://aris.test/abs/api/models/M1/attributes"
    assert body == {"attributes": {"kg_intelligence": "{}"}}


def test_path_overrides_apply():
    api = ArisApi(
        base_url="http://aris.test",
        token="t",
        paths={"models": "v2/repository/models"},
    )
    assert api.paths["models"] == "v2/repository/models"
    # untouched keys keep their defaults
    assert api.paths["model_objects"] == "models/{model_id}/objects"


def test_token_sets_bearer_header():
    api = ArisApi(base_url="http://aris.test", token="abc")
    assert api._session.headers["Authorization"] == "Bearer abc"
