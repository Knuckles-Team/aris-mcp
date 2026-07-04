"""Native epistemic-graph typed-node ingestion — Wire-First coverage for ARIS.

Exercises the real ``ingest_entities`` / ``ingest_models`` / ``ingest_model_graph``
seam with a fake engine client (no engine required), asserting the txn
add_node/commit + edge calls and the ARIS record → :ProcessModel/:EPC* mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from aris_mcp.kg_ingest import (
    ingest_entities,
    ingest_model_graph,
    ingest_models,
)


class _FakeTxn:
    def __init__(self):
        self.nodes = {}
        self.committed = False

    def begin(self, graph=None):
        self.graph = graph
        return "txn-1"

    def add_node(self, txn, node_id, props):
        self.nodes[node_id] = props

    def commit(self, txn):
        self.committed = True
        return True


class _FakeEdges:
    def __init__(self):
        self.edges = []

    def add(self, src, dst, props):
        self.edges.append((src, dst, props))


class _FakeClient:
    def __init__(self):
        self.txn = _FakeTxn()
        self.edges = _FakeEdges()


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "type": "ProcessModel", "name": "p"},
            {"id": "b", "type": "EPCFunction"},
        ],
        [{"source": "a", "target": "b", "type": "hasObject"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.txn.committed is True
    assert set(c.txn.nodes) == {"a", "b"}
    # provenance is stamped
    assert c.txn.nodes["a"]["source"] == "aris-mcp"
    assert c.txn.nodes["a"]["domain"] == "aris"
    assert c.edges.edges == [("a", "b", {"type": "hasObject"})]


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
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 0}
    m1 = c.txn.nodes["aris:model:M1"]
    assert m1["type"] == "ProcessModel"
    assert m1["name"] == "Order-to-Cash"
    assert m1["modelType"] == "EPC"
    assert m1["groupPath"] == "/Sales"
    assert m1["externalToolId"] == "M1"
    # id + name alias fallbacks resolve on the second record
    m2 = c.txn.nodes["aris:model:M2"]
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
    res = ingest_model_graph(model, objects, connections, client=c, graph="__commons__")
    # nodes: model + 3 objects + 1 reified connection = 5
    assert res["nodes"] == 5
    assert c.txn.nodes["aris:object:O1"]["type"] == "EPCEvent"
    assert c.txn.nodes["aris:object:O2"]["type"] == "EPCFunction"
    assert c.txn.nodes["aris:object:O3"]["type"] == "EPCRule"
    assert c.txn.nodes["aris:connection:C1"]["type"] == "ProcessConnection"
    edge_types = [e[2]["type"] for e in c.edges.edges]
    assert "hasObject" in edge_types
    assert "flowsTo" in edge_types
    assert "connectionSource" in edge_types
    assert "connectionTarget" in edge_types
    # the flowsTo edge for the reified connection maps object->object
    assert ("aris:object:O1", "aris:object:O2", {"type": "flowsTo"}) in c.edges.edges


def test_ingest_noops_without_engine():
    # No injected client + no reachable engine -> clean no-op.
    assert ingest_entities([{"id": "a", "type": "ProcessModel"}]) is None


def test_ingest_empty_is_noop():
    assert ingest_entities([], client=_FakeClient()) is None
    assert ingest_models([], client=_FakeClient()) is None
    assert ingest_model_graph({}, [], [], client=_FakeClient()) is None
