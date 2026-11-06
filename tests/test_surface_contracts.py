"""CONN-ARIS-MCP-CONNECTOR-CONTENT-R004, R005, R006: skills, prompts and tool-use contracts."""

import asyncio
import inspect
import json
import re
from pathlib import Path

import pytest
from scion_sdk.connector import build_server

from aris_mcp import connector_contracts as declared
from aris_mcp.mcp.mcp_aris import contracts_turtle

PACKAGE = Path(__file__).resolve().parents[1] / "aris_mcp"
PROMPTS = {
    p.stem: json.loads(p.read_text()) for p in (PACKAGE / "prompts").glob("*.json")
}
SKILLS = {p.parent.name for p in (PACKAGE / "skills").glob("*/SKILL.md")}
TOOL_NAME = re.compile(r"\baris_[a-z_]+\b")
NOT_TOOLS = {"aris_mcp"}


@pytest.fixture(scope="module")
def tools():
    _, mcp = build_server("aris_mcp", command_args=[])
    return {t.name: t for t in asyncio.run(mcp.list_tools())}


@pytest.mark.spec("CONN-ARIS-MCP-CONNECTOR-CONTENT-R006")
def test_every_tool_is_called_by_a_contract_and_named_by_a_link(tools):
    called = {s.tool for c in declared.CONTRACTS for s in c.steps}
    linked = {t for link in declared.LINKS for t in link.tools}
    assert called == set(tools) == linked


@pytest.mark.spec("CONN-ARIS-MCP-CONNECTOR-CONTENT-R006")
def test_steps_pass_real_parameters_and_declare_refusals(tools):
    for contract in declared.CONTRACTS:
        assert any(s.refusals for s in contract.steps), contract.task
        for step in contract.steps:
            props = set(tools[step.tool].parameters.get("properties", {}))
            assert set(step.params) <= props, (step.tool, set(step.params) - props)
            assert step.result, step.tool


@pytest.mark.spec("CONN-ARIS-MCP-CONNECTOR-CONTENT-R006")
def test_contracts_render_as_turtle_and_locations_read_through_tools(tools):
    text = contracts_turtle()
    assert "sc:ToolUseContract" in text and "sc:DataLocation" in text
    assert "ARIS_NOT_CONFIGURED" in text and "PROCESS_EXPORT_LOSSY" in text
    assert "owl:imports" not in text
    assert inspect.isfunction(contracts_turtle.__wrapped__)
    for loc in declared.LOCATIONS:
        assert loc.read_tool in tools
        assert loc.federation_key and loc.instance
    _, mcp = build_server("aris_mcp", command_args=[])
    uris = {str(r.uri) for r in asyncio.run(mcp.list_resources())}
    assert "ontology://aris-mcp/contracts.ttl" in uris


@pytest.mark.spec("CONN-ARIS-MCP-CONNECTOR-CONTENT-R004")
def test_skills_name_only_served_tools_and_link_to_tasks(tools):
    assert {
        "aris-process-modeling",
        "aris-process-mining",
        "aris-kg-ingestion",
        "aris-mcp-development",
        "aris-epc-to-canonical-workflow",
    } == SKILLS
    for skill in (PACKAGE / "skills").rglob("*.md"):
        text = skill.read_text()
        for tool in set(TOOL_NAME.findall(text)) - NOT_TOOLS:
            assert tool in tools, (skill.parent.name, tool)
    assert {s for link in declared.LINKS for s in link.skills} == SKILLS
    workflow = (PACKAGE / "skills" / "aris-epc-to-canonical-workflow" / "SKILL.md").read_text()
    for step in ("aris_import_aml", "aris_export_canonical_workflow", "ProcessPlan"):
        assert step in workflow


@pytest.mark.spec("CONN-ARIS-MCP-CONNECTOR-CONTENT-R005")
def test_prompts_are_complete_agent_definitions(tools):
    assert set(PROMPTS) == {"aris-process-operator", "aris-process-modeler"}
    locations = {loc.name for loc in declared.LOCATIONS}
    roles = {r.name for r in declared.ROLES}
    tasks = {c.task for c in declared.CONTRACTS}
    kinds = set()
    for name, doc in PROMPTS.items():
        agent = doc["agent"]
        kinds.add(agent["kind"])
        directive = doc["instructions"]["core_directive"]
        for section in ("GOAL", "TOOLS AND SKILLS", "DATA", "GUARDRAILS", "OUTPUT"):
            assert section in directive, (name, section)
        assert set(agent["tools"]) <= set(tools), name
        assert set(agent["skills"]) <= SKILLS, name
        assert set(agent["data"]["reads"]) | set(agent["data"]["writes"]) <= locations
        assert agent["guardrails"]["never"] and agent["outputs"], name
        for tool in set(TOOL_NAME.findall(directive)) - NOT_TOOLS:
            assert tool in tools, (name, tool)
        for tool in agent["tools"]:
            if not tools[tool].annotations.read_only_hint and "set_" in tool:
                assert tool in agent["guardrails"]["approval_required"], (name, tool)
        if agent["kind"] == "business-role":
            assert agent["business_role"] in roles
    assert kinds == {"operator", "business-role"}
    for link in declared.LINKS:
        assert link.task in tasks
        assert set(link.prompts) <= set(PROMPTS)
    assert {p for link in declared.LINKS for p in link.prompts} == set(PROMPTS)
