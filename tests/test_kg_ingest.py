"""Native epistemic-graph typed-node ingestion — Wire-First coverage for ARIS.

Exercises the real ``ingest_entities`` / ``ingest_models`` / ``ingest_model_graph``
seam against a fake transport boundary (no engine required), letting the SDK's own
``agent_connector_sdk.ingest`` request builder run on top of it. Unlike most fleet
connectors, ``aris_mcp.kg_ingest`` is a **best-effort** surface (its MCP tools must
never raise when the KG stack is down), so every entry point converts an unreachable
engine into ``None`` rather than propagating an error — those semantics are exercised
explicitly below. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent_connector_sdk.ingest import KnowledgeIngest

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
        return SimpleNamespace(accepted_checkpoint=None)

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
            {"id": "b", "node_type": "EPCFunction"},
        ],
        [{"source": "a", "target": "b", "relationship": "hasObject"}],
        ingest=service,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert {r.record_id for r in transport.requests[0].records} == {"a", "b"}
    assert transport.requests[0].relationships[0].relation_reference.endswith(
        "/relations/hasObject"
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
    # nodes: model + 3 objects + 1 reified connection = 5
    assert res["nodes"] == 5
    records = {r.record_id: r for r in transport.requests[0].records}
    assert records["aris:object:O1"].mapping_reference.endswith("/EPCEvent")
    assert records["aris:object:O2"].mapping_reference.endswith("/EPCFunction")
    assert records["aris:object:O3"].mapping_reference.endswith("/EPCRule")
    assert records["aris:connection:C1"].mapping_reference.endswith("/ProcessConnection")
    rel_refs = [r.relation_reference for r in transport.requests[0].relationships]
    assert any(ref.endswith("/relations/hasObject") for ref in rel_refs)
    assert any(ref.endswith("/relations/flowsTo") for ref in rel_refs)
    assert any(ref.endswith("/relations/connectionSource") for ref in rel_refs)
    assert any(ref.endswith("/relations/connectionTarget") for ref in rel_refs)
    # the flowsTo edge for the reified connection maps object->object
    flows = [
        r
        for r in transport.requests[0].relationships
        if r.relation_reference.endswith("/relations/flowsTo")
    ]
    assert any(
        r.source.record_id == "aris:object:O1" and r.target.record_id == "aris:object:O2"
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
    assert await ingest_entities([{"id": "a", "type": "ProcessModel"}], ingest=service) is None
    assert transport.requests == []


async def test_ingest_empty_is_noop(ingest):
    service, _ = ingest
    assert await ingest_entities([], ingest=service) is None
    assert await ingest_models([], ingest=service) is None
    assert await ingest_model_graph({}, [], [], ingest=service) is None
