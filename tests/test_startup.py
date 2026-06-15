"""Startup / wiring tests for aris-mcp (import-safe, write-gate honored)."""

from __future__ import annotations

import os


def test_package_imports():
    import aris_mcp
    from aris_mcp.api_client import ArisApi

    assert aris_mcp.__version__
    assert ArisApi is not None


def test_get_client_builds_from_env(monkeypatch):
    monkeypatch.setenv("ARIS_API_BASE", "http://aris.test/abs/api")
    monkeypatch.setenv("ARIS_TOKEN", "tok")
    # no OAuth vars → static bearer path
    monkeypatch.delenv("ARIS_OAUTH_URL", raising=False)
    from aris_mcp.auth import get_client

    client = get_client()
    assert client.base_url == "http://aris.test/abs/api/"
    assert client.token == "tok"


def test_write_gate_default_off(monkeypatch):
    monkeypatch.delenv("ARIS_ENABLE_WRITE", raising=False)
    from aris_mcp.mcp.mcp_aris import _writes_enabled

    assert _writes_enabled() is False
    os.environ["ARIS_ENABLE_WRITE"] = "True"
    try:
        assert _writes_enabled() is True
    finally:
        del os.environ["ARIS_ENABLE_WRITE"]
