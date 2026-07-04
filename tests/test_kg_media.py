"""Native epistemic-graph blob ingestion — Wire-First coverage for ARIS exports.

Exercises ``ingest_model_export`` with a fake MediaStore (no engine required),
asserting the store_media call carries the right media_type / mime / extra, and that
the seam cleanly no-ops without an engine. CONCEPT:AU-KG.ingest.list-durable-media.
"""

from __future__ import annotations

from aris_mcp.kg_media import ingest_model_export


class _StoredMedia:
    def __init__(self, asset_id, digest):
        self.asset_id = asset_id
        self.digest = digest


class _FakeStore:
    def __init__(self):
        self.calls = []

    def store_media(self, data, *, media_type, mime_type, source, name, extra):
        self.calls.append(
            {
                "size": len(data),
                "media_type": media_type,
                "mime_type": mime_type,
                "source": source,
                "name": name,
                "extra": extra,
            }
        )
        return _StoredMedia("asset-1", "deadbeef" * 8)


def test_ingest_model_export_stores_blob():
    store = _FakeStore()
    res = ingest_model_export(
        b"<bpmn>...</bpmn>",
        model_id="M1",
        model_name="Order-to-Cash",
        mime_type="application/bpmn+xml",
        export_format="bpmn",
        media_store=store,
    )
    assert res is not None
    assert res["asset_id"] == "asset-1"
    assert res["media_type"] == "document"
    assert res["size_bytes"] == len(b"<bpmn>...</bpmn>")
    call = store.calls[0]
    assert call["source"] == "aris-mcp"
    assert call["mime_type"] == "application/bpmn+xml"
    assert call["extra"]["model_id"] == "aris:model:M1"
    assert call["extra"]["asset_class"] == "ModelExport"
    assert call["extra"]["export_format"] == "bpmn"


def test_ingest_model_export_image_bucket():
    store = _FakeStore()
    ingest_model_export(
        b"\x89PNG...",
        model_id="M2",
        mime_type="image/png",
        media_store=store,
    )
    assert store.calls[0]["media_type"] == "image"


def test_ingest_empty_bytes_is_noop():
    store = _FakeStore()
    assert ingest_model_export(b"", model_id="M1", media_store=store) is None
    assert store.calls == []


def test_ingest_noops_without_engine():
    # No injected store + no reachable engine -> clean no-op.
    assert ingest_model_export(b"data", model_id="M1") is None
