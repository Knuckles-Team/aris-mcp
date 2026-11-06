"""CONN-ARIS-MCP-R008: the EPC and the BPMN version of one process are one workflow.

``invoice-approval.bpmn.canonical.json`` is the canonical form of
``invoice-approval.bpmn`` written by hand; ``bpmn_reference`` (test-only, the
reference for the engine's native BPMN reader) proves it from the BPMN file.
"""

import json
import sys
from pathlib import Path

import pytest

from aris_mcp.aml import read_aml
from aris_mcp.canonical import epc_to_canonical

sys.path.insert(0, str(Path(__file__).parent))
from bpmn_reference import bpmn_to_canonical  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _dag(canonical: dict) -> tuple[dict, set]:
    """The agent workflow graph: one node per canonical step, one edge per flow."""
    nodes = {s["id"]: (s["kind"], s["gate"], s["label"]) for s in canonical["steps"]}
    edges = {(f["source"], f["target"], f["condition"]) for f in canonical["flows"]}
    return nodes, edges


@pytest.mark.spec("CONN-ARIS-MCP-R008")
def test_epc_and_bpmn_give_the_same_digest_and_dag():
    [bundle] = read_aml((FIXTURES / "invoice-approval.aml").read_bytes())
    from_epc = epc_to_canonical(bundle.model, bundle.objects, bundle.connections)
    by_hand = json.loads((FIXTURES / "invoice-approval.bpmn.canonical.json").read_text())
    from_bpmn = bpmn_to_canonical((FIXTURES / "invoice-approval.bpmn").read_bytes())
    golden = json.loads((FIXTURES / "invoice-approval.canonical.json").read_text())

    assert from_bpmn == by_hand
    assert from_epc["digest"] == by_hand["digest"] == golden["digest"]
    assert from_epc["source"]["system"] == "aris"
    assert by_hand["source"]["system"] == "bpmn20"
    assert _dag(from_epc) == _dag(by_hand)

    nodes, edges = _dag(from_epc)
    assert len(nodes) == 12 and len(edges) == 13
    assert [nodes[f"s{i}"][:2] for i in range(1, 13)] == [
        ("start", None),
        ("human", None),
        ("decision", None),
        ("branch", "xor"),
        ("human", None),
        ("join", "xor"),
        ("agent", None),
        ("fork", "and"),
        ("agent", None),
        ("agent", None),
        ("join", "and"),
        ("end", None),
    ]
