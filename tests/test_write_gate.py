"""ARIS writes are refused unless ARIS_ENABLE_WRITE is set, on every surface."""

import pytest

from aris_mcp.api.api_client_aris import ArisApi


@pytest.mark.parametrize("method", ["set_model_attributes", "set_object_attributes"])
def test_client_writes_refuse_without_enablement(monkeypatch, method):
    monkeypatch.delenv("ARIS_ENABLE_WRITE", raising=False)
    api = ArisApi.__new__(ArisApi)
    api.request = lambda *a, **k: pytest.fail("write reached the transport")
    with pytest.raises(PermissionError, match="ARIS_ENABLE_WRITE"):
        getattr(api, method)("id-1", {"k": "v"})
