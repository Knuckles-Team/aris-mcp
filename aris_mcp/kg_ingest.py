"""Native knowledge-graph ingestion for ARIS records (typed graph nodes).

CONCEPT:AU-KG.ingest.enterprise-source-extractor. This package natively pushes its
ARIS process data into the knowledge graph as **typed OWL nodes** of the leaf
classes of ``aris.ttl`` (:EpcModel; :EpcHumanFunction / :EpcAutomatedFunction /
:EpcDecisionFunction / :EpcProcessInterface; :EpcStartEvent / :EpcEndEvent /
:EpcIntermediateEvent; :EpcAndOperator / :EpcOrOperator / :EpcXorOperator; the
attachment classes; a reified :EpcConnection per connection) + control-flow links, through the shared ``scion_sdk.ingest`` knowledge-ingest facade — the
one connector write path; there is no self-contained fallback transaction here.

Entirely best-effort: with no reachable engine, or a malformed record, every entry
point **no-ops** (returns ``None``), so the connector keeps working with zero KG
infrastructure. Nodes match the classes federated by ``aris_mcp.ontology`` (aris.ttl).

Only a thin mapper lives here (ARIS records → entity/relationship dicts); the write
path is the shared ``scion_sdk.ingest`` facade.
"""

from __future__ import annotations

import logging
from typing import Any

from scion_sdk.ingest import (
    ChangeSet,
    Entity,
    IngestBinding,
    IngestError,
    IngestUnavailableError,
    KnowledgeIngest,
    Relationship,
    current_ingest,
)

logger = logging.getLogger("aris_mcp.kg")

_SOURCE = "aris-mcp"
_DOMAIN = "aris"

_BINDING = IngestBinding(connector="aris-mcp", stream=_DOMAIN)

# ARIS records return under several key spellings depending on tenant/portal. These
# alias tuples make the mapper resilient across ARIS Connect ABS vs. the public API.
_ID_KEYS = ("guid", "id", "objectGuid", "modelGuid", "ID")
_NAME_KEYS = ("name", "Name", "label", "title")
_TYPE_KEYS = ("type", "typeName", "symbolType", "symbolName", "objectType", "modelType")


def _first(rec: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        v = rec.get(k)
        if v is not None and v != "":
            return v
    return None


def _to_entity(record: dict[str, Any]) -> Entity:
    return Entity(
        id=record.get("id"),
        node_type=record.get("node_type"),
        properties={k: v for k, v in record.items() if k not in ("id", "node_type")},
    )


def _to_relationship(record: dict[str, Any]) -> Relationship:
    props = {
        k: v for k, v in record.items() if k not in ("source", "target", "relationship")
    }
    return Relationship(
        source=record["source"],
        target=record["target"],
        relationship=record["relationship"],
        properties=props or None,
    )


async def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int] | None:
    """Write typed OWL nodes (+ edges) into the knowledge graph. Best-effort, never raises.

    ``entities``: ``[{"id":..., "node_type":<owl:Class>, ...props}]``.
    ``relationships``: ``[{"source":id, "target":id, "relationship":<link>}]``.
    Returns ``{"nodes":n, "edges":m}`` or ``None`` (empty input / no reachable engine /
    malformed record). ``ingest`` may be injected (tests); otherwise the process-wide
    facade is resolved on demand.
    """
    entities = [e for e in (entities or []) if e.get("id")]
    if not entities:
        return None
    change_set = ChangeSet(
        entities=tuple(_to_entity(e) for e in entities),
        relationships=tuple(_to_relationship(r) for r in relationships or ()),
    )
    try:
        service = ingest or current_ingest()
        receipt = await service.submit(_BINDING, change_set)
    except (IngestUnavailableError, IngestError) as exc:
        logger.debug("KG ingest unavailable/failed: %s", exc)
        return None
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


# ── ARIS-specific mappers ──────────────────────────────────────────────────
def _model_class(model: dict[str, Any]) -> str:
    from aris_mcp.vocabulary import vocabulary

    epc_types = vocabulary().classes["EpcModel"].type_nums
    return "EpcModel" if model.get("type") in epc_types else "ProcessModel"


async def ingest_models(
    models: list[dict[str, Any]],
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int] | None:
    """Map ARIS model records → :ProcessModel nodes and ingest."""
    entities: list[dict[str, Any]] = []
    for model in models or []:
        mid = _first(model, _ID_KEYS)
        if mid is None:
            continue
        entities.append(
            {
                "id": f"aris:model:{mid}",
                "node_type": _model_class(model),
                "name": _first(model, _NAME_KEYS),
                "guid": str(mid),
                "modelType": _first(model, _TYPE_KEYS),
                "groupPath": model.get("groupPath")
                or model.get("group")
                or model.get("database"),
                "externalToolId": str(mid),
            }
        )
    return await ingest_entities(entities, [], ingest=ingest)


def _model_node(model: dict[str, Any], model_id: str, mid: Any) -> dict[str, Any]:
    return {
        "id": model_id,
        "node_type": _model_class(model),
        "name": _first(model, _NAME_KEYS),
        "guid": str(mid),
        "modelType": _first(model, _TYPE_KEYS),
        "groupPath": model.get("groupPath")
        or model.get("group")
        or model.get("database"),
        "externalToolId": str(mid),
    }


def _object_entity_and_edge(
    obj: dict[str, Any], model_id: str, classes: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    oid = _first(obj, _ID_KEYS)
    if oid is None:
        return None
    obj_type = _first(obj, _TYPE_KEYS)
    node_id = f"aris:object:{oid}"
    node = {
        "id": node_id,
        "node_type": classes.get(str(oid), "EpcAttachment"),
        "name": _first(obj, _NAME_KEYS),
        "guid": str(oid),
        "objectType": obj_type,
        "symbolType": obj.get("symbol") or obj.get("symbolNum"),
        "externalToolId": str(oid),
    }
    edge = {"source": model_id, "target": node_id, "relationship": "hasObject"}
    return node, edge


def _connection_endpoints(conn: dict[str, Any]) -> tuple[Any, Any]:
    src = (
        conn.get("sourceObjectId")
        or conn.get("source")
        or conn.get("sourceGuid")
        or conn.get("from")
    )
    tgt = (
        conn.get("targetObjectId")
        or conn.get("target")
        or conn.get("targetGuid")
        or conn.get("to")
    )
    return src, tgt


def _reified_connection_entities(
    conn: dict[str, Any], model_id: str, src_id: str, tgt_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Emit the reified :EpcConnection node plus its hasConnection /
    connectionSource / connectionTarget edges. A connection without its own id
    gets one derived from the model, its endpoints and its type."""
    cid = _first(conn, _ID_KEYS)
    if cid is None:
        ctype = _first(conn, _TYPE_KEYS) or "cxn"
        cid = f"{model_id.removeprefix('aris:model:')}:{src_id.removeprefix('aris:object:')}:{tgt_id.removeprefix('aris:object:')}:{ctype}"
    conn_id = f"aris:connection:{cid}"
    node = {
        "id": conn_id,
        "node_type": "EpcConnection",
        "guid": str(cid),
        "connectionType": _first(conn, _TYPE_KEYS),
        "externalToolId": str(cid),
    }
    edges = [
        {"source": model_id, "target": conn_id, "relationship": "hasConnection"},
        {"source": conn_id, "target": src_id, "relationship": "connectionSource"},
        {"source": conn_id, "target": tgt_id, "relationship": "connectionTarget"},
    ]
    return node, edges


def _connection_entities_and_edges(
    conn: dict[str, Any], model_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Map one connection into its entities + relationships (:flowsTo, plus
    the reified :EpcConnection). Returns ([], []) if unusable
    (missing source/target)."""
    src, tgt = _connection_endpoints(conn)
    if src is None or tgt is None:
        return [], []
    src_id = f"aris:object:{src}"
    tgt_id = f"aris:object:{tgt}"

    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    node, edges = _reified_connection_entities(conn, model_id, src_id, tgt_id)
    entities.append(node)
    relationships.extend(edges)

    relationships.append(
        {"source": src_id, "target": tgt_id, "relationship": "flowsTo"}
    )
    return entities, relationships


async def ingest_model_graph(
    model: dict[str, Any],
    objects: list[dict[str, Any]] | None = None,
    connections: list[dict[str, Any]] | None = None,
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int] | None:
    """Map one model + its EPC objects + control-flow connections into the KG.

    Emits the model, each object as its leaf class of ``aris.ttl`` (typed by
    TypeNum/SymbolNum first, the type-name hints only as a fallback) with a
    :hasObject link, and each connection as a reified :EpcConnection node plus a
    :flowsTo edge.
    """
    from aris_mcp.canonical import classify_epc_objects

    mid = _first(model or {}, _ID_KEYS)
    if mid is None:
        return None
    model_id = f"aris:model:{mid}"

    entities: list[dict[str, Any]] = [_model_node(model, model_id, mid)]
    relationships: list[dict[str, Any]] = []

    classes = classify_epc_objects(list(objects or []), list(connections or []))
    for obj in objects or []:
        pair = _object_entity_and_edge(obj, model_id, classes)
        if pair is not None:
            node, edge = pair
            entities.append(node)
            relationships.append(edge)

    for conn in connections or []:
        conn_entities, conn_relationships = _connection_entities_and_edges(
            conn, model_id
        )
        entities.extend(conn_entities)
        relationships.extend(conn_relationships)

    return await ingest_entities(entities, relationships, ingest=ingest)
