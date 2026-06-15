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
