"""Native epistemic-graph blob ingestion for raw ARIS model exports.

CONCEPT:AU-KG.ingest.list-durable-media. An ARIS model can be exported as raw bytes
(BPMN/XML/AML, an SVG/PNG diagram render, or a PDF report). When a live epistemic-graph
engine is reachable, those bytes are stored as a content-addressed media record (a
``MediaAsset`` on an ``agent_connector_sdk.ingest.ChangeSet``, subclassed :ModelExport
in aris.ttl) in one commit. This makes the export itself — not just a model GUID —
durable, deduped, and queryable inside the knowledge graph.

Entirely best-effort: if no live engine is reachable, every entry point here **no-ops**
(returns ``None``), so aris-mcp keeps working with zero KG infrastructure.
"""

from __future__ import annotations

import logging
from typing import Any

from agent_connector_sdk.ingest import (
    ChangeSet,
    IngestBinding,
    IngestError,
    IngestUnavailableError,
    KnowledgeIngest,
    MediaAsset,
    current_ingest,
)

logger = logging.getLogger("aris_mcp.kg_media")

_SOURCE = "aris-mcp"

_BLOB_BINDING = IngestBinding(connector="aris-mcp", stream="aris", media_type="ModelExport")

# Common ARIS export MIME types → the coarse media_type bucket carried on the asset.
_XML_MIMES = ("application/xml", "text/xml", "application/bpmn+xml")


def _media_type(mime: str) -> str:
    m = (mime or "").lower()
    if m.startswith("image"):
        return "image"
    if m == "application/pdf":
        return "document"
    if m in _XML_MIMES or m.endswith("+xml") or m.startswith("text"):
        return "document"
    return "file"


async def ingest_model_export(
    data: bytes | None,
    *,
    model_id: str,
    model_name: str = "",
    mime_type: str = "application/xml",
    export_format: str = "",
    source: str = _SOURCE,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, Any] | None:
    """Store a raw ARIS model export as a content-addressed media record.

    ``model_id`` is the ARIS model GUID (matching ``aris:model:<guid>``). Returns
    ``{asset_id, digest, size_bytes, media_type}`` on success, or ``None`` when there
    is no engine, no bytes, or the commit failed (never raises). ``ingest`` may be
    injected (tests); otherwise the process-wide facade is resolved on demand.
    """
    if not data:
        return None

    media_type = _media_type(mime_type)
    name = model_name or f"aris-model-{model_id}"
    extra: dict[str, Any] = {
        "model_id": f"aris:model:{model_id}",
        "model_guid": str(model_id),
        "domain": "aris",
        "asset_class": "ModelExport",
    }
    if export_format:
        extra["export_format"] = export_format
    if model_name:
        extra["model_name"] = model_name

    asset = MediaAsset(data=data, mime_type=mime_type, name=name, properties=extra)
    change_set = ChangeSet(media=(asset,))
    try:
        service = ingest or current_ingest()
        receipt = await service.submit(_BLOB_BINDING, change_set)
    except (IngestUnavailableError, IngestError) as e:  # noqa: BLE001 — best-effort
        logger.warning("KG media ingest: submit failed: %s", e)
        return None

    admission = receipt.raw_admissions[-1] if receipt.raw_admissions else None
    asset_id = admission.record_id if admission else None
    digest = admission.raw_digest if admission else None
    logger.info(
        "KG media ingest: stored ARIS export %s (%s bytes) as asset %s",
        name,
        len(data),
        asset_id or "?",
    )
    return {
        "asset_id": asset_id,
        "digest": digest,
        "size_bytes": len(data),
        "media_type": media_type,
    }
