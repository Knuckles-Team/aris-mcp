"""CONN-ARIS-MCP-R004, R005: EPC <-> canonical workflow adapter."""

import copy
import json
from pathlib import Path

import pytest

from aris_mcp.aml import AmlModel, read_aml, write_aml
from aris_mcp.canonical import (
    SCHEMA,
    CanonicalError,
    canonical_to_epc,
    compute_digest,
    epc_to_canonical,
)
from aris_mcp.source import fixture_dir

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = json.loads((FIXTURES / "invoice-approval.canonical.json").read_text())


def _canonical(path: Path) -> dict:
    [bundle] = read_aml(path.read_bytes())
    return epc_to_canonical(bundle.model, bundle.objects, bundle.connections)


def _reimport(epc: dict) -> dict:
    [bundle] = read_aml(
        write_aml([AmlModel(epc["model"], epc["objects"], epc["connections"])])
    )
    return epc_to_canonical(bundle.model, bundle.objects, bundle.connections)


@pytest.mark.spec("CONN-ARIS-MCP-R004")
def test_epc_to_canonical_equals_the_golden():
    canonical = _canonical(FIXTURES / "invoice-approval.aml")
    assert canonical == GOLDEN
    assert canonical["schema"] == SCHEMA
    assert len(canonical["steps"]) == 12
    assert canonical["digest"] == compute_digest(canonical["steps"], canonical["flows"])
    kinds = [(s["kind"], s["gate"], s["label"]) for s in canonical["steps"]]
    assert kinds[:4] == [
        ("start", None, "Invoice received"),
        ("human", None, "Check invoice"),
        ("decision", None, "Determine approval level"),
        ("branch", "xor", ""),
    ]
    by_label = {s["label"]: s for s in canonical["steps"]}
    assert by_label["Check invoice"]["role"] == "Accounts payable"
    assert by_label["Approve invoice"]["role"] == "Finance manager"
    assert by_label["Post invoice"]["kind"] == "agent"
    assert by_label["Post invoice"]["role"] == "Accounts payable"
    assert by_label["Determine approval level"]["ref"] == "approval-level"
    conditions = {f["condition"] for f in canonical["flows"] if f["condition"]}
    assert conditions == {"Amount at most 1000", "Amount above 1000"}
    folded = {a["label"] for a in canonical["annex"]}
    assert {
        "Invoice checked",
        "Invoice approved",
        "Invoice posted",
        "Supplier notified",
        "Invoice archived",
        "Amount at most 1000",
        "Amount above 1000",
    } == folded


@pytest.mark.spec("CONN-ARIS-MCP-R004")
def test_or_process_interface_and_unknown_attachment():
    canonical = _canonical(fixture_dir() / "supplier-onboarding.aml")
    kinds = {s["label"]: (s["kind"], s["gate"]) for s in canonical["steps"]}
    assert kinds["Compliance screening"] == ("call", None)
    gates = {(s["kind"], s["gate"]) for s in canonical["steps"] if s["gate"]}
    assert gates == {("fork", "or"), ("join", "or")}
    attachment = [a for a in canonical["annex"] if a["construct"] == "epc-attachment"]
    assert attachment and attachment[0]["label"] == "Supplier fraud risk"
    assert attachment[0]["type_num"] == "OT_RISK"


@pytest.mark.spec("CONN-ARIS-MCP-R004")
def test_text_is_normalised_and_digest_ignores_name_source_annex():
    canonical = copy.deepcopy(GOLDEN)
    renamed = dict(canonical, name="Other", source={}, annex=[], losses=[])
    assert compute_digest(renamed["steps"], renamed["flows"]) == GOLDEN["digest"]
    [bundle] = read_aml((FIXTURES / "invoice-approval.aml").read_bytes())
    for obj in bundle.objects:
        if obj["name"] == "Check invoice":
            obj["name"] = "  Check   invoice "
    again = epc_to_canonical(bundle.model, bundle.objects, bundle.connections)
    assert again["digest"] == GOLDEN["digest"]


@pytest.mark.spec("CONN-ARIS-MCP-R005")
@pytest.mark.parametrize(
    "path",
    [FIXTURES / "invoice-approval.aml", fixture_dir() / "supplier-onboarding.aml"],
)
def test_same_source_round_trip_keeps_digest_and_annex(path):
    first = _canonical(path)
    epc = canonical_to_epc(first, strict=True)
    assert epc["losses"] == []
    second = _reimport(epc)
    assert second["digest"] == first["digest"]
    assert second["annex"] == first["annex"]
    assert second["source"] == first["source"]


def _lossy() -> dict:
    canonical = copy.deepcopy(GOLDEN)
    steps, flows = canonical["steps"], canonical["flows"]
    steps.append(
        {
            "id": "s13",
            "kind": "wait",
            "gate": None,
            "label": "Supplier reply",
            "role": None,
            "ref": "message:supplier-reply",
        }
    )
    steps.append(
        {
            "id": "s14",
            "kind": "boundary",
            "gate": None,
            "label": "Approval overdue",
            "role": None,
            "ref": "timer:P2D",
        }
    )
    flows.append(
        {"source": "s10", "target": "s13", "condition": None, "default": False}
    )
    flows.append({"source": "s5", "target": "s14", "condition": None, "default": False})
    for flow in flows:
        if flow["condition"] == "Amount at most 1000":
            flow["default"] = True
    canonical["digest"] = compute_digest(steps, flows)
    return canonical


@pytest.mark.spec("CONN-ARIS-MCP-R005")
def test_strict_export_refuses_lossy_constructs():
    with pytest.raises(CanonicalError) as refused:
        canonical_to_epc(_lossy(), strict=True)
    assert refused.value.code == "PROCESS_EXPORT_LOSSY"
    constructs = {loss["construct"] for loss in refused.value.details}
    assert {"typed-trigger", "boundary-event", "default-flow"} <= constructs


@pytest.mark.spec("CONN-ARIS-MCP-R005")
def test_lenient_export_lists_losses_and_restores_alternation():
    epc = canonical_to_epc(_lossy(), strict=False)
    losses = {(loss["element"], loss["construct"]) for loss in epc["losses"]}
    assert ("s13", "typed-trigger") in losses
    assert ("s14", "boundary-event") in losses
    assert ("s4", "default-flow") in losses
    assert all(loss["target"] == "epc" and loss["treatment"] for loss in epc["losses"])
    names = {o["name"] for o in epc["objects"]}
    assert "Supplier reply (message:supplier-reply)" in names


@pytest.mark.spec("CONN-ARIS-MCP-R005")
def test_cross_source_export_synthesises_events_and_lists_other_annex():
    bpmn = json.loads((FIXTURES / "invoice-approval.bpmn.canonical.json").read_text())
    bpmn["annex"] = [
        {"after": "s2", "construct": "bpmn-preserved-xml", "element_id": "x"}
    ]
    with pytest.raises(CanonicalError):
        canonical_to_epc(bpmn, strict=True)
    epc = canonical_to_epc(bpmn, strict=False)
    constructs = {loss["construct"] for loss in epc["losses"]}
    assert constructs == {"bpmn-preserved-xml", "decision-table"}
    names = {o["name"] for o in epc["objects"]}
    assert "Check invoice completed" in names
    assert _reimport(epc)["digest"] == GOLDEN["digest"]


@pytest.mark.spec("CONN-ARIS-MCP-R005")
def test_invalid_canonical_is_refused():
    for bad in ({"schema": "x"}, "not json", {**GOLDEN, "digest": "0" * 64}):
        with pytest.raises(CanonicalError) as refused:
            canonical_to_epc(bad)
        assert refused.value.code == "PROCESS_CANONICAL_INVALID"
