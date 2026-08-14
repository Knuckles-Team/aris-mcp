"""Native epistemic-graph ingestion for ARIS records (typed graph nodes).

CONCEPT:AU-KG.ingest.enterprise-source-extractor. This package natively pushes its
ARIS process data into the epistemic-graph knowledge graph as **typed OWL nodes**
(:ProcessModel, :EPCFunction, :EPCEvent, :EPCRule, :ProcessConnection) + control-flow
links, through the required ``agent_utilities.knowledge_graph.memory.native_ingest``
authority — the one connector write path; there is no self-contained fallback
transaction here.

Entirely best-effort: with no agent-utilities KG stack, no reachable engine, or a
malformed record, every entry point **no-ops** (returns ``None``), so the connector
keeps working with zero KG infrastructure. Nodes carry the shared provenance
(``domain``/``source``) and match the classes federated by ``aris_mcp.ontology``
(aris.ttl).

Only a thin mapper lives here (ARIS records → entity/relationship dicts); the write
path is the shared ``native_ingest`` primitive.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_utilities.knowledge_graph.memory.native_ingest import (
    NativeIngestError,
    ingest_entities as _native_ingest_entities,
)

logger = logging.getLogger("aris_mcp.kg")

_SOURCE = "aris-mcp"
_DOMAIN = "aris"

# ARIS records return under several key spellings depending on tenant/portal. These
# alias tuples make the mapper resilient across ARIS Connect ABS vs. the public API.
_ID_KEYS = ("guid", "id", "objectGuid", "modelGuid", "ID")
_NAME_KEYS = ("name", "Name", "label", "title")
_TYPE_KEYS = ("type", "typeName", "symbolType", "symbolName", "objectType", "modelType")

# ARIS symbol/type substrings → the EPC object subclass to tag.
_EVENT_HINTS = ("event",)
_RULE_HINTS = ("rule", "operator", "connector", "and", "or", "xor")


def _first(rec: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        v = rec.get(k)
        if v is not None and v != "":
            return v
    return None


def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Write typed OWL nodes (+ edges) into epistemic-graph. Best-effort, never raises.

    ``entities``: ``[{"id":..., "node_type":<owl:Class>, ...props}]``.
    ``relationships``: ``[{"source":id, "target":id, "relationship":<link>}]``.
    Returns ``{"nodes":n, "edges":m}`` or ``None`` (empty input / no reachable engine /
    malformed record). ``client``/``graph`` may be injected (tests); otherwise the
    process-owned governed authority is resolved on demand.
    """
    entities = [e for e in (entities or []) if e.get("id")]
    if not entities:
        return None
    try:
        return _native_ingest_entities(
            entities,
            relationships,
            source=source,
            domain=domain,
            client=client,
            graph=graph,
        )
    except NativeIngestError as exc:
        logger.debug("KG ingest unavailable/failed: %s", exc)
        return None


# ── ARIS-specific mappers ──────────────────────────────────────────────────
def _epc_class(obj_type: Any) -> str:
    """Classify an ARIS object's symbol/type string into an EPC subclass."""
    t = str(obj_type or "").lower()
    if any(h in t for h in _EVENT_HINTS):
        return "EPCEvent"
    if any(h in t for h in _RULE_HINTS):
        return "EPCRule"
    return "EPCFunction"


def ingest_models(
    models: list[dict[str, Any]],
    *,
    client: Any | None = None,
    graph: str | None = None,
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
                "node_type": "ProcessModel",
                "name": _first(model, _NAME_KEYS),
                "guid": str(mid),
                "modelType": _first(model, _TYPE_KEYS),
                "groupPath": model.get("groupPath")
                or model.get("group")
                or model.get("database"),
                "externalToolId": str(mid),
            }
        )
    return ingest_entities(entities, [], client=client, graph=graph)


def ingest_model_graph(
    model: dict[str, Any],
    objects: list[dict[str, Any]] | None = None,
    connections: list[dict[str, Any]] | None = None,
    *,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Map one model + its EPC objects + control-flow connections into the KG.

    Emits the :ProcessModel, each object as its :EPCFunction/:EPCEvent/:EPCRule
    subclass with a :hasObject link, and each connection as :flowsTo edges (+ a
    reified :ProcessConnection node when it carries its own guid/type).
    """
    mid = _first(model or {}, _ID_KEYS)
    if mid is None:
        return None
    model_id = f"aris:model:{mid}"

    entities: list[dict[str, Any]] = [
        {
            "id": model_id,
            "node_type": "ProcessModel",
            "name": _first(model, _NAME_KEYS),
            "guid": str(mid),
            "modelType": _first(model, _TYPE_KEYS),
            "groupPath": model.get("groupPath")
            or model.get("group")
            or model.get("database"),
            "externalToolId": str(mid),
        }
    ]
    relationships: list[dict[str, Any]] = []

    for obj in objects or []:
        oid = _first(obj, _ID_KEYS)
        if oid is None:
            continue
        obj_type = _first(obj, _TYPE_KEYS)
        node_id = f"aris:object:{oid}"
        entities.append(
            {
                "id": node_id,
                "node_type": _epc_class(obj_type),
                "name": _first(obj, _NAME_KEYS),
                "guid": str(oid),
                "objectType": obj_type,
                "externalToolId": str(oid),
            }
        )
        relationships.append(
            {"source": model_id, "target": node_id, "relationship": "hasObject"}
        )

    for conn in connections or []:
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
        if src is None or tgt is None:
            continue
        src_id = f"aris:object:{src}"
        tgt_id = f"aris:object:{tgt}"
        cid = _first(conn, _ID_KEYS)
        if cid is not None:
            conn_id = f"aris:connection:{cid}"
            entities.append(
                {
                    "id": conn_id,
                    "node_type": "ProcessConnection",
                    "guid": str(cid),
                    "connectionType": _first(conn, _TYPE_KEYS),
                    "externalToolId": str(cid),
                }
            )
            relationships.append(
                {"source": model_id, "target": conn_id, "relationship": "hasConnection"}
            )
            relationships.append(
                {
                    "source": conn_id,
                    "target": src_id,
                    "relationship": "connectionSource",
                }
            )
            relationships.append(
                {
                    "source": conn_id,
                    "target": tgt_id,
                    "relationship": "connectionTarget",
                }
            )
        relationships.append(
            {"source": src_id, "target": tgt_id, "relationship": "flowsTo"}
        )

    return ingest_entities(entities, relationships, client=client, graph=graph)
