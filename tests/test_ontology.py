"""CONN-ARIS-MCP-CONNECTOR-CONTENT-R003: the EPC ontology maps EPC to the
canonical workflow and rolls up to core by subclassing."""

import asyncio
import re

import pytest
from scion_sdk.connector import build_server

from aris_mcp.vocabulary import (
    CANONICAL_KINDS,
    GATES,
    SOURCE_ONLY_KINDS,
    ontology_text,
    parse_classes,
    vocabulary,
)

ID = "CONN-ARIS-MCP-CONNECTOR-CONTENT-R003"
TTL = ontology_text()
CLASSES = parse_classes(TTL)
CORE_OWNED = ("EpcFunction", "EpcRuleOperator", "ProcessEventType", "flowsTo")


@pytest.mark.spec(ID)
def test_every_class_reaches_a_core_class():
    for name in CLASSES:
        seen, todo, reached = set(), [name], False
        while todo:
            cls = todo.pop()
            if cls in seen:
                continue
            seen.add(cls)
            if cls not in CLASSES:
                reached = True  # a core class (http://knuckles.team/kg#)
                continue
            parents = CLASSES[cls].parents
            assert parents, f"{cls} has no rdfs:subClassOf"
            todo += parents
        assert reached, name


@pytest.mark.spec(ID)
def test_no_import_and_core_terms_are_only_parents():
    assert "owl:imports" not in TTL
    for term in CORE_OWNED:
        assert not re.search(rf"^:{term} a ", TTL, re.M), term
    assert {"EpcFunction"} == set(CLASSES["EpcHumanFunction"].parents)
    assert {"EpcRuleOperator"} == set(CLASSES["EpcXorOperator"].parents)
    assert {"ProcessEventType"} == set(CLASSES["EpcEvent"].parents)
    for retired in (
        "EPCObject",
        "EPCFunction",
        "EPCEvent",
        "EPCRule",
        "ProcessConnection",
    ):
        assert retired not in TTL, retired


@pytest.mark.spec(ID)
def test_dag_node_kinds_are_the_closed_set_and_gates_are_declared():
    kinds = {c.kind for c in CLASSES.values() if c.kind}
    assert kinds <= CANONICAL_KINDS | SOURCE_ONLY_KINDS
    assert {"human", "agent", "decision", "call", "start", "end", "state"} <= kinds
    gates = {
        c.name: (c.gate, c.kind, c.symbol_nums) for c in CLASSES.values() if c.gate
    }
    assert gates == {
        "EpcAndOperator": ("and", "fork", ("ST_OPR_AND_1",)),
        "EpcOrOperator": ("or", "fork", ("ST_OPR_OR_1",)),
        "EpcXorOperator": ("xor", "branch", ("ST_OPR_XOR_1",)),
    }
    assert {c.gate for c in CLASSES.values() if c.gate} == GATES
    assert CLASSES["EpcProcessInterface"].symbol_nums == ("ST_PRCS_IF",)


@pytest.mark.spec(ID)
def test_every_tool_named_by_executed_by_tool_is_served():
    _, mcp = build_server("aris_mcp", command_args=[])
    tools = {t.name for t in asyncio.run(mcp.list_tools())}
    named = {t for c in CLASSES.values() for t in c.tools}
    assert named and named <= tools


@pytest.mark.spec(ID)
def test_the_adapter_mapping_is_read_from_the_ontology():
    vocab = vocabulary()
    assert vocab.function_type_nums == {"OT_FUNC"}
    assert vocab.event_type_nums == {"OT_EVT"}
    assert vocab.rule_type_nums == {"OT_RULE"}
    assert vocab.attachment_class("OT_POS").name == "EpcOrganizationalElement"
    assert vocab.attachment_class("OT_DP_FUNC_TYPE").attachment_role == "it-support"
    assert vocab.attachment_class("OT_DMN_DECISION").attachment_role == "decision-rule"
    assert vocab.attachment_class("OT_RISK") is None
    edited = TTL.replace('"ST_OPR_XOR_1"', '"ST_OPR_XOR_2"')
    assert parse_classes(edited)["EpcXorOperator"].symbol_nums == ("ST_OPR_XOR_2",)
