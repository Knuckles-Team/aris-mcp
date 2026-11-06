"""CONN-ARIS-MCP-R007: one typed tool per operation; no routed or untyped tools."""

import asyncio

import pytest
from scion_sdk.connector import build_server
from scion_sdk.mcp.method_tools import UNTYPED_TOOLS_ATTRIBUTE

EXPECTED = {
    "aris_get_source_status",
    "aris_list_models",
    "aris_get_model",
    "aris_list_model_objects",
    "aris_list_model_connections",
    "aris_get_model_attributes",
    "aris_set_model_attributes",
    "aris_set_object_attributes",
    "aris_ingest_model_inventory",
    "aris_ingest_model_graph",
    "aris_ingest_model_export",
    "aris_import_aml",
    "aris_export_aml",
    "aris_export_canonical_workflow",
    "aris_import_canonical_workflow",
}


@pytest.fixture(scope="module")
def served():
    _, mcp = build_server("aris_mcp", command_args=[])
    return mcp, {t.name: t for t in asyncio.run(mcp.list_tools())}


@pytest.mark.spec("CONN-ARIS-MCP-R007")
def test_surface_is_one_typed_tool_per_operation(served):
    mcp, tools = served
    assert set(tools) == EXPECTED
    for name, tool in tools.items():
        props = tool.parameters.get("properties", {})
        assert "action" not in props and "params_json" not in props, name
        assert "split-action" not in tool.tags, name
        assert tool.annotations is not None, name
    assert not getattr(mcp, UNTYPED_TOOLS_ATTRIBUTE, set())
    for retired in ("aris_model", "aris_object", "aris_ingest_models"):
        assert retired not in tools


@pytest.mark.spec("CONN-ARIS-MCP-R007")
def test_parameters_are_typed_and_reads_are_read_only(served):
    _, tools = served
    assert tools["aris_get_model"].parameters["required"] == ["model_id"]
    assert (
        tools["aris_import_canonical_workflow"].parameters["properties"]["strict"][
            "type"
        ]
        == "boolean"
    )
    assert (
        tools["aris_set_model_attributes"].parameters["properties"]["attributes"][
            "type"
        ]
        == "object"
    )
    for name in ("aris_list_models", "aris_get_model", "aris_export_aml"):
        assert tools[name].annotations.read_only_hint is True, name
    assert tools["aris_set_object_attributes"].annotations.read_only_hint is False
