"""Native epistemic-graph typed-node ingestion — Wire-First coverage for ARIS.

Exercises the real ``ingest_entities`` / ``ingest_models`` / ``ingest_model_graph``
seam against a fake transport boundary (no engine required), letting the SDK's own
``scion_sdk.ingest`` request builder run on top of it. Unlike most fleet
connectors, ``aris_mcp.kg_ingest`` is a **best-effort** surface (its MCP tools must
never raise when the KG stack is down), so every entry point converts an unreachable
engine into ``None`` rather than propagating an error — those semantics are exercised
explicitly below. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from scion_sdk.ingest import KnowledgeIngest

from aris_mcp.kg_ingest import (
    ingest_entities,
    ingest_model_graph,
    ingest_models,
)

pytestmark = pytest.mark.asyncio


class _FakeTransport:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    async def source_status(self, connector: str, stream: str) -> Any:
        return SimpleNamespace(
            connector=connector, stream=stream, accepted_checkpoint=None
        )

    async def submit(self, request: Any) -> Any:
        self.requests.append(request)
        return SimpleNamespace(
            affected_count=len(request.records),
            relationship_count=len(request.relationships),
            raw_admissions=[],
        )

    async def store_blob(self, data: bytes) -> str:
        raise AssertionError("this test does not exercise blob storage")


@pytest.fixture
def ingest():
    transport = _FakeTransport()
    return KnowledgeIngest(transport, loop=None), transport


async def test_ingest_entities_writes_nodes_and_edges(ingest):
    service, transport = ingest
    res = await ingest_entities(
        [
            {"id": "a", "node_type": "ProcessModel", "name": "p"},
            {"id": "b", "node_type": "EpcAutomatedFunction"},
        ],
        [{"source": "a", "target": "b", "relationship": "hasObject"}],
        ingest=service,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert {r.record_id for r in transport.requests[0].records} == {"a", "b"}
    assert (
        transport.requests[0].relationships[0].relation_reference.endswith("/hasObject")
    )


async def test_ingest_models_maps_process_models(ingest):
    service, transport = ingest
    res = await ingest_models(
        [
            {
                "guid": "M1",
                "name": "Order-to-Cash",
                "type": "EPC",
                "groupPath": "/Sales",
            },
            {"id": "M2", "Name": "Hire-to-Retire", "modelType": "VACD"},
        ],
        ingest=service,
    )
    assert res == {"nodes": 2, "edges": 0}
    records = {r.record_id: r for r in transport.requests[0].records}
    m1 = records["aris:model:M1"]
    assert m1.payload["name"] == "Order-to-Cash"
    assert m1.payload["modelType"] == "EPC"
    assert m1.payload["groupPath"] == "/Sales"
    assert m1.payload["externalToolId"] == "M1"
    # id + name alias fallbacks resolve on the second record
    m2 = records["aris:model:M2"]
    assert m2.payload["name"] == "Hire-to-Retire"
    assert m2.payload["modelType"] == "VACD"


async def test_ingest_model_graph_classifies_epc_and_links_flow(ingest):
    service, transport = ingest
    model = {"guid": "M1", "name": "Order-to-Cash", "type": "EPC"}
    objects = [
        {"guid": "O1", "name": "Order received", "type": "Event"},
        {"guid": "O2", "name": "Check credit", "type": "Function"},
        {"guid": "O3", "name": "XOR", "type": "Rule operator"},
    ]
    connections = [
        {
            "guid": "C1",
            "sourceObjectId": "O1",
            "targetObjectId": "O2",
            "type": "activates",
        },
        {"sourceObjectId": "O2", "targetObjectId": "O3"},
    ]
    res = await ingest_model_graph(model, objects, connections, ingest=service)
    # nodes: model + 3 objects + 2 reified connections (one with a derived id) = 6
    assert res["nodes"] == 6
    records = {r.record_id: r for r in transport.requests[0].records}
    # no TypeNum: the type-name hints are the fallback
    assert records["aris:object:O1"].mapping_reference.endswith("/EpcStartEvent")
    assert records["aris:object:O2"].mapping_reference.endswith("/EpcAutomatedFunction")
    assert records["aris:object:O3"].mapping_reference.endswith("/EpcXorOperator")
    assert records["aris:connection:C1"].mapping_reference.endswith("/EpcConnection")
    assert "aris:connection:M1:O2:O3:cxn" in records
    rel_refs = [r.relation_reference for r in transport.requests[0].relationships]
    assert any(ref.endswith("/hasObject") for ref in rel_refs)
    assert any(ref.endswith("/flowsTo") for ref in rel_refs)
    assert any(ref.endswith("/connectionSource") for ref in rel_refs)
    assert any(ref.endswith("/connectionTarget") for ref in rel_refs)
    # the flowsTo edge for the reified connection maps object->object
    flows = [
        r
        for r in transport.requests[0].relationships
        if r.relation_reference.endswith("/flowsTo")
    ]
    assert any(
        r.source.record_id == "aris:object:O1"
        and r.target.record_id == "aris:object:O2"
        for r in flows
    )


async def test_ingest_noops_without_engine():
    # No injected service + no reachable engine -> clean no-op (best-effort surface).
    assert await ingest_entities([{"id": "a", "node_type": "ProcessModel"}]) is None


async def test_ingest_rejects_missing_node_type_as_noop(ingest):
    # aris_mcp's tool surface is best-effort (never raises): a malformed record
    # (missing the canonical ``node_type``) still reaches the SDK's own validation,
    # which this seam reports back as a clean no-op rather than propagating IngestError.
    service, transport = ingest
    assert (
        await ingest_entities([{"id": "a", "type": "ProcessModel"}], ingest=service)
        is None
    )
    assert transport.requests == []


async def test_ingest_empty_is_noop(ingest):
    service, _ = ingest
    assert await ingest_entities([], ingest=service) is None
    assert await ingest_models([], ingest=service) is None
    assert await ingest_model_graph({}, [], [], ingest=service) is None


@pytest.mark.spec("CONN-ARIS-MCP-CONNECTOR-CONTENT-R003")
async def test_ingest_types_nodes_by_typenum_and_symbol(ingest):
    """TypeNum/SymbolNum decide the leaf class; attachments decide the function kind."""
    from pathlib import Path

    from aris_mcp.aml import read_aml

    service, transport = ingest
    fixture = Path(__file__).parent / "fixtures" / "invoice-approval.aml"
    [bundle] = read_aml(fixture.read_bytes())
    await ingest_model_graph(
        bundle.model, bundle.objects, bundle.connections, ingest=service
    )
    by_name = {
        r.payload.get("name"): r.mapping_reference.rsplit("/", 1)[-1]
        for r in transport.requests[0].records
    }
    assert by_name["Invoice approval"] == "EpcModel"
    assert by_name["Check invoice"] == "EpcHumanFunction"
    assert by_name["Post invoice"] == "EpcAutomatedFunction"
    assert by_name["Determine approval level"] == "EpcDecisionFunction"
    assert by_name["Invoice received"] == "EpcStartEvent"
    assert by_name["Invoice checked"] == "EpcIntermediateEvent"
    assert by_name["Invoice processed"] == "EpcEndEvent"
    assert by_name["Accounts payable"] == "EpcOrganizationalElement"
    assert by_name["ERP system"] == "EpcApplicationSystem"
    assert by_name["approval-level"] == "EpcBusinessRule"
    assert by_name["Invoice"] == "EpcDocument"
    kinds = {
        r.mapping_reference.rsplit("/", 1)[-1] for r in transport.requests[0].records
    }
    assert {"EpcXorOperator", "EpcAndOperator", "EpcConnection"} <= kinds
    connections = [
        r
        for r in transport.requests[0].records
        if r.record_id.startswith("aris:connection:")
    ]
    assert len(connections) == len(bundle.connections)
