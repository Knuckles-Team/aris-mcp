"""CONN-ARIS-MCP-R001, R006: source resolution, typed refusals, health, fixture repository."""

import asyncio
import json
import logging

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from scion_sdk.connector import build_server
from starlette.testclient import TestClient

from aris_mcp.source import resolve_mode, source_status

SOURCE_VARS = ("ARIS_API_BASE", "ARIS_REPOSITORY_DIR", "ARIS_ENABLE_WRITE")


@pytest.fixture
def env(monkeypatch):
    for var in SOURCE_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def _server():
    return build_server("aris_mcp", command_args=[])[1]


async def _call(name: str, args: dict | None = None):
    async with Client(_server()) as client:
        return (await client.call_tool(name, args or {})).structured_content


async def _refusal(name: str, args: dict | None = None) -> dict:
    """The JSON refusal body. The tool raises ToolError; the SDK error middleware
    delivers it as a JSON-RPC error whose message ends with the same body."""
    async with Client(_server()) as client:
        with pytest.raises((ToolError, MCPError)) as raised:
            await client.call_tool(name, args or {})
    text = str(raised.value)
    return json.loads(text[text.index("{") :])


@pytest.mark.spec("CONN-ARIS-MCP-R001")
def test_mode_resolution(env, tmp_path):
    assert resolve_mode().mode == "unconfigured"
    env.setenv("ARIS_REPOSITORY_DIR", str(tmp_path))
    assert resolve_mode().mode == "files"
    env.setenv("ARIS_REPOSITORY_DIR", "fixture")
    assert resolve_mode().mode == "fixture"
    env.setenv("ARIS_API_BASE", "https://aris.example.com/abs/api")
    assert resolve_mode().mode == "live"


@pytest.mark.spec("CONN-ARIS-MCP-R001")
@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("aris_list_models", {}),
        ("aris_get_model", {"model_id": "m"}),
        ("aris_list_model_objects", {"model_id": "m"}),
        ("aris_list_model_connections", {"model_id": "m"}),
        ("aris_get_model_attributes", {"model_id": "m"}),
        ("aris_set_model_attributes", {"model_id": "m", "attributes": {"a": "b"}}),
        ("aris_set_object_attributes", {"object_id": "o", "attributes": {"a": "b"}}),
        ("aris_ingest_model_inventory", {}),
        ("aris_ingest_model_graph", {"model_id": "m"}),
        ("aris_export_aml", {"model_id": "m"}),
        ("aris_export_canonical_workflow", {"model_id": "m"}),
    ],
)
def test_unconfigured_refuses_typed(env, tool, args):
    body = asyncio.run(_refusal(tool, args))
    assert body["code"] == "ARIS_NOT_CONFIGURED"
    assert "ARIS_API_BASE" in body["remedy"] and "ARIS_REPOSITORY_DIR" in body["remedy"]
    assert body["message"]


@pytest.mark.spec("CONN-ARIS-MCP-R001")
def test_unconfigured_server_starts_answers_health_and_status(env):
    seen: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            seen.append(record.getMessage())

    handler = _Capture()
    logging.getLogger("aris_mcp.source").addHandler(handler)
    try:
        mcp = _server()
    finally:
        logging.getLogger("aris_mcp.source").removeHandler(handler)
    assert "aris-mcp source mode: unconfigured" in seen
    assert len(asyncio.run(mcp.list_tools())) == 15
    with TestClient(mcp.http_app()) as client:
        assert client.get("/health").status_code == 200
    status = asyncio.run(_call("aris_get_source_status"))
    assert status["mode"] == "unconfigured" and status["writes_enabled"] is False
    assert "ARIS_REPOSITORY_DIR" in status["remedy"]


@pytest.mark.spec("CONN-ARIS-MCP-R001")
def test_health_in_every_mode(env, tmp_path):
    for mode_env in (
        {"ARIS_REPOSITORY_DIR": "fixture"},
        {"ARIS_REPOSITORY_DIR": str(tmp_path)},
        {"ARIS_API_BASE": "https://aris.example.com/abs/api"},
    ):
        for key, value in mode_env.items():
            env.setenv(key, value)
        with TestClient(_server().http_app()) as client:
            assert client.get("/health").status_code == 200
        for key in mode_env:
            env.delenv(key)


@pytest.mark.spec("CONN-ARIS-MCP-R001")
def test_write_refusals(env, tmp_path):
    env.setenv("ARIS_REPOSITORY_DIR", "fixture")
    args = {"model_id": "m", "attributes": {"AT_DESC": "x"}}
    body = asyncio.run(_refusal("aris_set_model_attributes", args))
    assert body["code"] == "ARIS_READ_ONLY_SOURCE"
    env.delenv("ARIS_REPOSITORY_DIR")
    env.setenv("ARIS_API_BASE", "https://aris.example.com/abs/api")
    env.setenv("ARIS_TOKEN", "tok")
    body = asyncio.run(_refusal("aris_set_model_attributes", args))
    assert body["code"] == "ARIS_WRITE_DISABLED"


@pytest.mark.spec("CONN-ARIS-MCP-R006")
def test_fixture_repository_serves_the_samples_through_read_tools(env):
    env.setenv("ARIS_REPOSITORY_DIR", "fixture")
    status = asyncio.run(_call("aris_get_source_status"))
    assert status["mode"] == "fixture" and status["model_count"] == 2
    listed = asyncio.run(_call("aris_list_models"))
    assert listed["repository"] == "fixture"
    names = {m["name"]: m["guid"] for m in listed["items"]}
    assert set(names) == {"Invoice approval", "Supplier onboarding"}
    guid = names["Invoice approval"]
    model = asyncio.run(_call("aris_get_model", {"model_id": guid}))
    assert model["repository"] == "fixture" and model["model"]["type"] == "MT_EEPC"
    objects = asyncio.run(_call("aris_list_model_objects", {"model_id": guid}))
    connections = asyncio.run(_call("aris_list_model_connections", {"model_id": guid}))
    assert len(objects["items"]) == 24 and len(connections["items"]) == 28
    assert objects["repository"] == connections["repository"] == "fixture"
    canonical = asyncio.run(_call("aris_export_canonical_workflow", {"model_id": guid}))
    assert len(canonical["steps"]) == 12
    aml = asyncio.run(_call("aris_export_aml", {"model_id": guid}))
    assert aml["aml"].startswith("<?xml") and aml["repository"] == "fixture"
    missing = asyncio.run(_refusal("aris_get_model", {"model_id": "nope"}))
    assert missing["code"] == "ARIS_MODEL_NOT_FOUND"


@pytest.mark.spec("CONN-ARIS-MCP-R006")
def test_files_repository_reads_an_aml_directory(env, tmp_path):
    from aris_mcp.source import fixture_dir

    (tmp_path / "one.aml").write_bytes(
        (fixture_dir() / "supplier-onboarding.aml").read_bytes()
    )
    (tmp_path / "broken.aml").write_text("<AML><Group>")
    env.setenv("ARIS_REPOSITORY_DIR", str(tmp_path))
    status = source_status()
    assert status == {
        "mode": "files",
        "repository": str(tmp_path),
        "model_count": 1,
        "writes_enabled": False,
    }
    listed = asyncio.run(_call("aris_list_models", {"name": "onboard"}))
    assert listed["repository"] == "files" and listed["count"] == 1
