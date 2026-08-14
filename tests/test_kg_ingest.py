"""Native epistemic-graph typed-node ingestion — Wire-First coverage for ARIS.

Exercises the real ``ingest_entities`` / ``ingest_models`` / ``ingest_model_graph``
seam with a fake ChangeEnvelope-capable engine client (no engine required), asserting
the committed nodes/edges and the ARIS record → :ProcessModel/:EPC* mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.

The fake client mirrors agent-utilities' own sanctioned test double
(``agent-utilities/tests/knowledge_graph/test_native_ingest.py``) — the ``txn``-only
fake is retired; ``native_ingest`` now hard-requires an injected client exposing
``.changes``/``.nodes``/``.rdf``/``.supports()``. Unlike most fleet connectors,
``aris_mcp.kg_ingest`` is a **best-effort** surface (its MCP tools must never raise
when the KG stack is down), so it converts ``NativeIngestError`` into ``None`` rather
than propagating it — those semantics are exercised explicitly below.
"""

from __future__ import annotations

from typing import Any

import msgpack
import pytest
from agent_utilities.knowledge_graph.core.session import GraphSession, use_session
from agent_utilities.models.company_brain import ActorType
from agent_utilities.security.brain_context import ActorContext, use_actor

from aris_mcp.kg_ingest import (
    ingest_entities,
    ingest_model_graph,
    ingest_models,
)


@pytest.fixture(autouse=True)
def _governed_session():
    actor = ActorContext(
        actor_id="subject:opaque:synthetic",
        actor_type=ActorType.AUTOMATED_SERVICE,
        roles=(),
        tenant_id="tenant:opaque:synthetic",
        authenticated=True,
    )
    session = GraphSession(
        actor=actor,
        tenant=actor.tenant_id,
        scopes=frozenset({"kg:write"}),
        graph="graph:opaque:synthetic",
        policy_version="policy:opaque:synthetic",
        audience="epistemic-graph",
    )
    with use_actor(actor), use_session(session):
        yield


class _FakeNodes:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def properties(self, node_id: str) -> dict[str, Any] | None:
        return self.values.get(node_id)

    def list(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self.values.items())


class _FakeChanges:
    def __init__(self, nodes: _FakeNodes) -> None:
        self.nodes = nodes
        self.edges: list[tuple[str, str, dict[str, Any]]] = []
        self.applied: list[dict[str, Any]] = []
        self.records: dict[str, dict[str, Any]] = {}
        self.versions: dict[str, dict[str, Any]] = {}

    def get(self, envelope_id: str) -> dict[str, Any] | None:
        return self.records.get(envelope_id)

    def content_version(self, object_id: str) -> dict[str, Any] | None:
        return self.versions.get(object_id)

    def cursor(self, _source: str, _partition: str = "") -> None:
        return None

    def apply(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.applied.append(envelope)
        mutation = envelope["mutation"]
        for operation in mutation["operations"]:
            method = operation["method"]
            params = method["params"]
            properties = msgpack.unpackb(params["properties_msgpack"], raw=False)
            if method["method"] == "AddNode":
                self.nodes.values[params["node_id"]] = properties
            elif method["method"] == "AddEdge":
                self.edges.append(
                    (params["source_id"], params["target_id"], properties)
                )
        version = envelope["content_version"]
        self.versions[version["object_id"]] = version
        self.records[envelope["envelope_id"]] = envelope
        return {
            "batch_id": mutation["batch_id"],
            "replayed": False,
            "projection_pending": False,
        }


class _FakeRdf:
    def validate_shacl(self, _shapes: str, _data_graph: str) -> dict[str, Any]:
        return {"conforms": True, "results": []}


class _FakeClient:
    def __init__(self) -> None:
        self.nodes = _FakeNodes()
        self.changes = _FakeChanges(self.nodes)
        self.rdf = _FakeRdf()

    @staticmethod
    def supports(operation: str) -> bool:
        return operation == "ApplyChangeEnvelope"


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "node_type": "ProcessModel", "name": "p"},
            {"id": "b", "node_type": "EPCFunction"},
        ],
        [{"source": "a", "target": "b", "relationship": "hasObject"}],
        client=c,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert set(c.nodes.values) == {"a", "b"}
    # provenance is stamped
    assert c.nodes.values["a"]["source"] == "aris-mcp"
    assert c.nodes.values["a"]["domain"] == "aris"
    assert c.changes.edges == [("a", "b", {"relationship": "hasObject"})]


def test_ingest_models_maps_process_models():
    c = _FakeClient()
    res = ingest_models(
        [
            {
                "guid": "M1",
                "name": "Order-to-Cash",
                "type": "EPC",
                "groupPath": "/Sales",
            },
            {"id": "M2", "Name": "Hire-to-Retire", "modelType": "VACD"},
        ],
        client=c,
    )
    assert res == {"nodes": 2, "edges": 0}
    m1 = c.nodes.values["aris:model:M1"]
    assert m1["node_type"] == "ProcessModel"
    assert m1["name"] == "Order-to-Cash"
    assert m1["modelType"] == "EPC"
    assert m1["groupPath"] == "/Sales"
    assert m1["externalToolId"] == "M1"
    # id + name alias fallbacks resolve on the second record
    m2 = c.nodes.values["aris:model:M2"]
    assert m2["name"] == "Hire-to-Retire"
    assert m2["modelType"] == "VACD"


def test_ingest_model_graph_classifies_epc_and_links_flow():
    c = _FakeClient()
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
    res = ingest_model_graph(model, objects, connections, client=c)
    # nodes: model + 3 objects + 1 reified connection = 5
    assert res["nodes"] == 5
    assert c.nodes.values["aris:object:O1"]["node_type"] == "EPCEvent"
    assert c.nodes.values["aris:object:O2"]["node_type"] == "EPCFunction"
    assert c.nodes.values["aris:object:O3"]["node_type"] == "EPCRule"
    assert c.nodes.values["aris:connection:C1"]["node_type"] == "ProcessConnection"
    edge_types = [e[2]["relationship"] for e in c.changes.edges]
    assert "hasObject" in edge_types
    assert "flowsTo" in edge_types
    assert "connectionSource" in edge_types
    assert "connectionTarget" in edge_types
    # the flowsTo edge for the reified connection maps object->object
    assert (
        "aris:object:O1",
        "aris:object:O2",
        {"relationship": "flowsTo"},
    ) in c.changes.edges


def test_ingest_noops_without_engine():
    # No injected client + no reachable engine -> clean no-op (best-effort surface).
    assert ingest_entities([{"id": "a", "node_type": "ProcessModel"}]) is None


def test_ingest_rejects_retired_structural_alias_as_noop():
    # aris_mcp's tool surface is best-effort (never raises): a malformed record
    # (the retired ``type`` alias instead of canonical ``node_type``) is reported
    # back as a clean no-op rather than propagating NativeIngestError.
    c = _FakeClient()
    assert ingest_entities([{"id": "a", "type": "ProcessModel"}], client=c) is None
    assert c.changes.applied == []


def test_ingest_empty_is_noop():
    assert ingest_entities([], client=_FakeClient()) is None
    assert ingest_models([], client=_FakeClient()) is None
    assert ingest_model_graph({}, [], [], client=_FakeClient()) is None
