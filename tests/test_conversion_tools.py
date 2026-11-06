"""CONN-ARIS-MCP-R004, R005, R002: the conversion tools work without a repository."""

import asyncio
import base64
import json
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from scion_sdk.connector import build_server

FIXTURES = Path(__file__).parent / "fixtures"
AML = (FIXTURES / "invoice-approval.aml").read_text()
GOLDEN = json.loads((FIXTURES / "invoice-approval.canonical.json").read_text())


@pytest.fixture(autouse=True)
def unconfigured(monkeypatch):
    for var in ("ARIS_API_BASE", "ARIS_REPOSITORY_DIR"):
        monkeypatch.delenv(var, raising=False)


async def _run(name, args):
    _, mcp = build_server("aris_mcp", command_args=[])
    async with Client(mcp) as client:
        return (await client.call_tool(name, args)).structured_content


async def _refused(name, args):
    _, mcp = build_server("aris_mcp", command_args=[])
    async with Client(mcp) as client:
        with pytest.raises((ToolError, MCPError)) as raised:
            await client.call_tool(name, args)
    text = str(raised.value)
    return json.loads(text[text.index("{") :])


@pytest.mark.spec("CONN-ARIS-MCP-R004")
def test_export_canonical_workflow_from_aml_text_unconfigured():
    canonical = asyncio.run(_run("aris_export_canonical_workflow", {"aml_text": AML}))
    assert canonical == GOLDEN
    b64 = base64.b64encode(AML.encode()).decode()
    imported = asyncio.run(_run("aris_import_aml", {"aml_b64": b64}))
    assert imported["models"][0]["model"]["name"] == "Invoice approval"


@pytest.mark.spec("CONN-ARIS-MCP-R005")
def test_import_canonical_workflow_tool_strict_and_lenient():
    lossy = json.loads(json.dumps(GOLDEN))
    for flow in lossy["flows"]:
        if flow["condition"] == "Amount at most 1000":
            flow["default"] = True
    lossy["digest"] = ""
    body = asyncio.run(
        _refused("aris_import_canonical_workflow", {"canonical": lossy, "strict": True})
    )
    assert body["code"] == "PROCESS_EXPORT_LOSSY"
    assert body["details"][0]["construct"] == "default-flow"
    out = asyncio.run(
        _run("aris_import_canonical_workflow", {"canonical": GOLDEN, "strict": True})
    )
    assert out["losses"] == [] and out["aml"].startswith("<?xml")


@pytest.mark.spec("CONN-ARIS-MCP-R002")
def test_planted_doctype_is_refused_by_the_tool():
    planted = '<?xml version="1.0"?><!DOCTYPE AML [<!ENTITY e SYSTEM "file:///etc/passwd">]><AML>&e;</AML>'
    body = asyncio.run(_refused("aris_import_aml", {"aml_text": planted}))
    assert body["code"] == "AML_INVALID"
