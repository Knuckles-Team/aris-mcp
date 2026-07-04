"""Thin MCP wrappers around the ARIS API client.

Each tool parses params, calls the corresponding :class:`~aris_mcp.api.api_client_aris.ArisApi`
method, and returns the result. All API surface lives in ``aris_mcp.api`` — these
tools add no business logic. Writes are gated by ``ARIS_ENABLE_WRITE`` (default
off) so a read-only tenant/credential cannot be asked to mutate models.
"""

import json
import os
from typing import Any

from agent_utilities.base_utilities import to_boolean
from fastmcp import FastMCP
from pydantic import Field

from aris_mcp.auth import get_client


def _p(params_json: str) -> dict[str, Any]:
    return json.loads(params_json) if params_json else {}


def _writes_enabled() -> bool:
    return to_boolean(os.getenv("ARIS_ENABLE_WRITE", "False"))


def register_aris_tools(mcp: FastMCP) -> None:
    """Register ARIS model/object read + (gated) write tools."""

    @mcp.tool(tags={"model"})
    async def aris_model(
        action: str = Field(
            description=(
                "Model action: 'list' (inventory), 'get' (one model), "
                "'objects' (EPC functions/events/rules), 'connections' "
                "(control flow), 'attributes' (read), 'set_attributes' (write, "
                "requires ARIS_ENABLE_WRITE)."
            )
        ),
        params_json: str = Field(
            default="{}",
            description=(
                'JSON args. get/objects/connections/attributes: {"model_id":..}; '
                'set_attributes: {"model_id":..,"attributes":{...}}; '
                "list: optional filter fields."
            ),
        ),
    ) -> Any:
        """Work with ARIS models and their EPC structure."""
        api = get_client()
        p = _p(params_json)
        if action == "list":
            return api.list_models(p or None)
        if action == "get":
            return api.get_model(p["model_id"])
        if action == "objects":
            return api.list_model_objects(p["model_id"])
        if action == "connections":
            return api.list_model_connections(p["model_id"])
        if action == "attributes":
            return api.list_model_attributes(p["model_id"])
        if action == "set_attributes":
            if not _writes_enabled():
                raise PermissionError(
                    "ARIS writes are disabled — set ARIS_ENABLE_WRITE=True to enable."
                )
            return api.set_model_attributes(p["model_id"], p.get("attributes", {}))
        raise ValueError(f"Unknown aris_model action: {action!r}.")

    @mcp.tool(tags={"object"})
    async def aris_object(
        action: str = Field(
            description="Object action: 'set_attributes' (write, requires ARIS_ENABLE_WRITE)."
        ),
        params_json: str = Field(
            default="{}",
            description='JSON args: {"object_id":..,"attributes":{...}}.',
        ),
    ) -> Any:
        """Write attributes on a single ARIS object."""
        api = get_client()
        p = _p(params_json)
        if action == "set_attributes":
            if not _writes_enabled():
                raise PermissionError(
                    "ARIS writes are disabled — set ARIS_ENABLE_WRITE=True to enable."
                )
            return api.set_object_attributes(p["object_id"], p.get("attributes", {}))
        raise ValueError(f"Unknown aris_object action: {action!r}.")

    @mcp.tool(tags={"model", "kg"})
    async def aris_ingest_models(
        params_json: str = Field(
            default="{}",
            description=(
                "JSON args. Empty/omit → ingest the whole model inventory as "
                ':ProcessModel nodes. {"model_id":..} → ingest ONE model with its '
                "EPC objects (:EPCFunction/:EPCEvent/:EPCRule) + control-flow "
                "(:flowsTo) connections. list filters may be passed alongside."
            ),
        ),
    ) -> Any:
        """Natively ingest ARIS models into epistemic-graph as typed nodes.

        Lists via the real ARIS client and pushes typed OWL nodes + links through the
        fast engine client. Best-effort: returns ``{"ingested": None}`` when no engine
        is reachable. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
        """
        from aris_mcp.kg_ingest import ingest_model_graph, ingest_models

        api = get_client()
        p = _p(params_json)
        model_id = p.pop("model_id", None)
        if model_id:
            model = api.get_model(model_id)
            objects = api.list_model_objects(model_id)
            connections = api.list_model_connections(model_id)
            model = model if isinstance(model, dict) else {"guid": model_id}
            objects = objects if isinstance(objects, list) else []
            connections = connections if isinstance(connections, list) else []
            result = ingest_model_graph(model, objects, connections)
            return {
                "model_id": model_id,
                "objects": len(objects),
                "connections": len(connections),
                "ingested": result,
            }
        models = api.list_models(p or None)
        models = models if isinstance(models, list) else [models]
        models = [m for m in models if isinstance(m, dict)]
        result = ingest_models(models)
        return {"listed": len(models), "ingested": result}

    @mcp.tool(tags={"model", "kg"})
    async def aris_ingest_model_export(
        params_json: str = Field(
            default="{}",
            description=(
                "JSON args to store a raw model export blob as a :ModelExport "
                '(:MediaAsset): {"model_id":.., "data_b64":<base64 bytes>, '
                '"mime_type":"application/xml", "model_name":.., '
                '"export_format":"bpmn|aml|svg|pdf"}.'
            ),
        ),
    ) -> Any:
        """Store a raw ARIS model export (bytes) as a content-addressed KG blob.

        The export bytes are supplied base64-encoded (rendered/exported out-of-band by
        the caller), stored via ``MediaStore`` as a :Blob + :ModelExport node linked to
        its :ProcessModel. Best-effort no-op when no engine is reachable.
        CONCEPT:AU-KG.ingest.list-durable-media.
        """
        import base64

        from aris_mcp.kg_media import ingest_model_export

        p = _p(params_json)
        model_id = p.get("model_id")
        if not model_id:
            raise ValueError("aris_ingest_model_export requires 'model_id'.")
        raw = p.get("data_b64") or ""
        data = base64.b64decode(raw) if raw else b""
        result = ingest_model_export(
            data,
            model_id=str(model_id),
            model_name=p.get("model_name", ""),
            mime_type=p.get("mime_type", "application/xml"),
            export_format=p.get("export_format", ""),
        )
        return {"model_id": model_id, "size_bytes": len(data), "ingested": result}
