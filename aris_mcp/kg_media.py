"""Native epistemic-graph blob ingestion for raw ARIS model exports.

CONCEPT:AU-KG.ingest.list-durable-media. An ARIS model can be exported as raw bytes
(BPMN/XML/AML, an SVG/PNG diagram render, or a PDF report). When a live epistemic-graph
engine is reachable, those bytes are stored as a content-addressed **blob** with a
``:MediaAsset`` graph node (subclassed :ModelExport in aris.ttl) in ONE cross-modal ACID
commit, via the agent-utilities ``MediaStore``. This makes the export itself — not just a
model GUID — durable, deduped, and queryable inside the knowledge graph.

Entirely best-effort and dependency-guarded: if agent-utilities' KG stack or a live
engine is not present, every entry point here **no-ops** (returns ``None``), so aris-mcp
keeps working with zero KG infrastructure.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("aris_mcp.kg_media")

_SOURCE = "aris-mcp"

# Common ARIS export MIME types → the coarse media_type bucket carried on the asset.
_XML_MIMES = ("application/xml", "text/xml", "application/bpmn+xml")


def _media_store() -> Any | None:
    """Build a ``MediaStore`` over a live engine, or ``None`` when unavailable.

    Prefers the shared ``native_ingest.media_store`` primitive; falls back to building
    a ``MediaStore`` directly when the primitive is not present in the installed
    ``agent_utilities``.
    """
    try:
        from agent_utilities.knowledge_graph.memory.native_ingest import (
            media_store as _shared_media_store,
        )

        store = _shared_media_store()
        if store is not None:
            return store
    except Exception as e:  # noqa: BLE001 — primitive absent; use local fallback
        logger.debug("native_ingest.media_store unavailable, falling back: %s", e)

    try:
        from agent_utilities.knowledge_graph.core.graph_compute import (
            GraphComputeEngine,
        )
        from agent_utilities.knowledge_graph.memory.media_store import MediaStore
    except Exception as e:  # noqa: BLE001 — agent-utilities KG stack absent
        logger.debug("KG media ingest unavailable (import): %s", e)
        return None
    try:
        engine = GraphComputeEngine()
        if getattr(engine, "_client", None) is None:
            logger.debug("KG media ingest: no live engine client")
            return None
        return MediaStore(engine)
    except Exception as e:  # noqa: BLE001 — no reachable engine
        logger.debug("KG media ingest: engine unreachable: %s", e)
        return None


def _media_type(mime: str) -> str:
    m = (mime or "").lower()
    if m.startswith("image"):
        return "image"
    if m == "application/pdf":
        return "document"
    if m in _XML_MIMES or m.endswith("+xml") or m.startswith("text"):
        return "document"
    return "file"


def ingest_model_export(
    data: bytes | None,
    *,
    model_id: str,
    model_name: str = "",
    mime_type: str = "application/xml",
    export_format: str = "",
    source: str = _SOURCE,
    media_store: Any | None = None,
) -> dict[str, Any] | None:
    """Store a raw ARIS model export as a blob + :ModelExport (:MediaAsset) node.

    ``model_id`` is the ARIS model GUID (matching ``aris:model:<guid>``). Returns
    ``{asset_id, digest, size_bytes, media_type}`` on success, or ``None`` when there
    is no engine, no bytes, or the store failed (never raises). ``media_store`` may be
    injected (tests); otherwise one is built on demand.
    """
    if not data:
        return None
    store = media_store if media_store is not None else _media_store()
    if store is None:
        return None

    media_type = _media_type(mime_type)
    name = model_name or f"aris-model-{model_id}"
    extra = {
        "model_id": f"aris:model:{model_id}",
        "model_guid": str(model_id),
        "domain": "aris",
        "asset_class": "ModelExport",
    }
    if export_format:
        extra["export_format"] = export_format
    if model_name:
        extra["model_name"] = model_name

    try:
        stored = store.store_media(
            data,
            media_type=media_type,
            mime_type=mime_type,
            source=source,
            name=name,
            extra=extra,
        )
    except Exception as e:  # noqa: BLE001 — engine/store failure is non-fatal
        logger.warning("KG media ingest: store_media failed: %s", e)
        return None
    if stored is None:
        return None

    logger.info(
        "KG media ingest: stored ARIS export %s (%s bytes) as asset %s digest %s",
        name,
        len(data),
        stored.asset_id,
        stored.digest[:16],
    )
    return {
        "asset_id": stored.asset_id,
        "digest": stored.digest,
        "size_bytes": len(data),
        "media_type": media_type,
    }
