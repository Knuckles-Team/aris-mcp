"""Native epistemic-graph blob ingestion — Wire-First coverage for ARIS exports.

Exercises ``ingest_model_export`` against a fake transport boundary (no engine
required), asserting the content-addressed media record carries the right
media_type / mime / provenance, and that the seam cleanly no-ops without an engine.
CONCEPT:AU-KG.ingest.list-durable-media.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent_connector_sdk.ingest import KnowledgeIngest

from aris_mcp.kg_media import ingest_model_export

pytestmark = pytest.mark.asyncio


class _FakeTransport:
    def __init__(self) -> None:
        self.stored: list[bytes] = []
        self.requests: list[Any] = []

    async def source_status(self, connector: str, stream: str) -> Any:
        return SimpleNamespace(accepted_checkpoint=None)

    async def store_blob(self, data: bytes) -> str:
        self.stored.append(data)
        return f"digest-{len(self.stored)}"

    async def submit(self, request: Any) -> Any:
        self.requests.append(request)
        record = request.records[0]
        return SimpleNamespace(
            affected_count=len(request.records),
            relationship_count=len(request.relationships),
            raw_admissions=[
                SimpleNamespace(
                    record_id=record.record_id,
                    raw_digest="a" * 64,
                    stream=record.stream,
                    deduplicated=False,
                )
            ],
        )


def _service():
    transport = _FakeTransport()
    return KnowledgeIngest(transport, loop=None), transport


async def test_ingest_model_export_stores_blob():
    service, transport = _service()
    res = await ingest_model_export(
        b"<bpmn>...</bpmn>",
        model_id="M1",
        model_name="Order-to-Cash",
        mime_type="application/bpmn+xml",
        export_format="bpmn",
        ingest=service,
    )
    assert res is not None
    assert res["asset_id"] is not None
    assert res["media_type"] == "document"
    assert res["size_bytes"] == len(b"<bpmn>...</bpmn>")
    assert transport.stored == [b"<bpmn>...</bpmn>"]
    record = transport.requests[0].records[0]
    assert record.payload["model_id"] == "aris:model:M1"
    assert record.payload["asset_class"] == "ModelExport"
    assert record.payload["export_format"] == "bpmn"


async def test_ingest_model_export_image_bucket():
    service, _ = _service()
    res = await ingest_model_export(
        b"\x89PNG...",
        model_id="M2",
        mime_type="image/png",
        ingest=service,
    )
    assert res["media_type"] == "image"


async def test_ingest_empty_bytes_is_noop():
    service, transport = _service()
    assert await ingest_model_export(b"", model_id="M1", ingest=service) is None
    assert transport.stored == []


async def test_ingest_noops_without_engine():
    # No injected service + no reachable engine -> clean no-op.
    assert await ingest_model_export(b"data", model_id="M1") is None
