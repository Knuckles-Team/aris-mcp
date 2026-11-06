"""TEST-ONLY reference BPMN 2.0 -> canonical workflow reader.

This is not part of the connector: BPMN is read natively by the engine
(section 4 of the canonical process contract). It exists to prove the
cross-source equivalence fixture and serves as the reference behaviour for the
engine's native reader: userTask/manualTask -> human; serviceTask/scriptTask/
sendTask/task/intermediateThrowEvent -> agent; businessRuleTask -> decision;
receiveTask/intermediateCatchEvent/eventBasedGateway -> wait; subProcess/
callActivity -> call; boundaryEvent -> boundary; startEvent -> start; endEvent ->
end; exclusive/parallel/inclusive gateway -> xor/and/or by degree; complexGateway
refuses PROCESS_IMPORT_UNMAPPED_ELEMENT. Lane -> role; a sequence flow's
conditionExpression (or its name) -> condition; the gateway default -> default.
"""

from __future__ import annotations

from typing import Any

from defusedxml import ElementTree as SafeET

from aris_mcp.canonical import CanonicalError, _Node, build_canonical

BPMN = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
OPERATON = "{http://operaton.org/schema/1.0/bpmn}"

_KIND = {
    "userTask": "human",
    "manualTask": "human",
    "serviceTask": "agent",
    "scriptTask": "agent",
    "sendTask": "agent",
    "task": "agent",
    "intermediateThrowEvent": "agent",
    "businessRuleTask": "decision",
    "receiveTask": "wait",
    "intermediateCatchEvent": "wait",
    "eventBasedGateway": "wait",
    "subProcess": "call",
    "callActivity": "call",
    "boundaryEvent": "boundary",
    "startEvent": "start",
    "endEvent": "end",
}
_GATE = {"exclusiveGateway": "xor", "parallelGateway": "and", "inclusiveGateway": "or"}


def bpmn_to_canonical(data: bytes) -> dict[str, Any]:
    root = SafeET.fromstring(data, forbid_dtd=True)
    process = root.find(f"{BPMN}process")
    assert process is not None
    lanes = {
        ref.text: lane.get("name")
        for lane in process.iter(f"{BPMN}lane")
        for ref in lane.findall(f"{BPMN}flowNodeRef")
    }
    flows_xml = process.findall(f"{BPMN}sequenceFlow")
    out_deg: dict[str, int] = {}
    in_deg: dict[str, int] = {}
    for f in flows_xml:
        out_deg[f.get("sourceRef")] = out_deg.get(f.get("sourceRef"), 0) + 1
        in_deg[f.get("targetRef")] = in_deg.get(f.get("targetRef"), 0) + 1
    nodes: dict[str, _Node] = {}
    defaults = set()
    for elem in process:
        tag = elem.tag.removeprefix(BPMN)
        eid = elem.get("id", "")
        if elem.get("default"):
            defaults.add(elem.get("default"))
        if tag == "complexGateway":
            raise CanonicalError("PROCESS_IMPORT_UNMAPPED_ELEMENT", eid)
        if tag in _GATE:
            gate = _GATE[tag]
            kind = (
                ("branch" if gate == "xor" else "fork")
                if out_deg.get(eid, 0) >= 2
                else "join"
            )
            nodes[eid] = _Node(eid, kind, gate, elem.get("name") or "", element=eid)
        elif tag in _KIND:
            kind = _KIND[tag]
            gate = "xor" if tag == "eventBasedGateway" else None
            ref = None
            if kind == "decision":
                ref = elem.get(f"{OPERATON}decisionRef")
            elif kind == "call":
                ref = elem.get("calledElement") or elem.get("name")
            role = lanes.get(eid) or elem.get(f"{OPERATON}candidateGroups")
            nodes[eid] = _Node(
                eid, kind, gate, elem.get("name") or "", role, ref, element=eid
            )
    flows = []
    for f in flows_xml:
        cond = f.find(f"{BPMN}conditionExpression")
        text = (cond.text or "").strip() if cond is not None else ""
        flows.append(
            (
                f.get("sourceRef"),
                f.get("targetRef"),
                text or f.get("name") or None,
                f.get("id") in defaults,
            )
        )
    return build_canonical(
        process.get("name") or "",
        nodes,
        flows,
        system="bpmn20",
        model_id=process.get("id") or "",
    )
