"""Software AG ARIS REST API wrapper.

Client for the ARIS REST API (ARIS Connect / ARIS Enterprise / ARIS Cloud)
covering the surface the agent-utilities KG ARIS extractor and the outbound
process-intelligence writeback consume:

* **read** — model inventory, per-model EPC objects (functions/events/rules) and
  their control-flow connections, and attribute read-back.
* **write** — model / object attribute writes (the outbound ``kg_intelligence``
  enrichment); gated at the MCP-tool layer by ``ARIS_ENABLE_WRITE``.

ARIS deployments differ (Connect ABS portal vs the public ARIS API; on-prem vs
Cloud), so the **endpoint path templates are configurable** — pass overrides
(or set the matching env vars in :mod:`aris_mcp.auth`) to match your tenant.
The defaults follow the common ARIS Connect ABS REST layout
(``{base}/models``, ``{base}/models/{id}/objects`` …). Method names are stable;
only the paths move.
"""

from typing import Any

from aris_mcp.api.api_client_base import ApiClientBase

# Default ARIS Connect ABS REST path templates. Override per tenant if needed.
DEFAULT_PATHS = {
    "models": "models",
    "model": "models/{model_id}",
    "model_objects": "models/{model_id}/objects",
    "model_connections": "models/{model_id}/connections",
    "model_attributes": "models/{model_id}/attributes",
    "object_attributes": "objects/{object_id}/attributes",
}


class ArisApi(ApiClientBase):
    """Read/write client for an ARIS REST API tenant."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify: bool = True,
        paths: dict[str, str] | None = None,
    ):
        super().__init__(
            base_url, token=token, username=username, password=password, verify=verify
        )
        self.paths = {**DEFAULT_PATHS, **(paths or {})}

    # ── reads (consumed by the KG ARIS extractor) ──────────────────────────
    def list_models(self, params: dict[str, Any] | None = None) -> Any:
        """List models in the tenant/database (process + architecture)."""
        return self.request("GET", self.paths["models"], params=params)

    def get_model(self, model_id: str) -> Any:
        """Get a single model's metadata (including its attributes)."""
        return self.request(
            "GET", self.paths["model"].format(model_id=model_id)
        )

    def list_model_objects(self, model_id: str) -> Any:
        """List the EPC objects (functions/events/rule operators) of a model."""
        return self.request(
            "GET", self.paths["model_objects"].format(model_id=model_id)
        )

    def list_model_connections(self, model_id: str) -> Any:
        """List the directed control-flow connections between a model's objects."""
        return self.request(
            "GET", self.paths["model_connections"].format(model_id=model_id)
        )

    def list_model_attributes(self, model_id: str) -> Any:
        """Get a model's attributes (used for writeback idempotency read-back)."""
        return self.request(
            "GET", self.paths["model_attributes"].format(model_id=model_id)
        )

    # ── writes (outbound enrichment; gated by ARIS_ENABLE_WRITE at the tool) ─
    def set_model_attributes(
        self, model_id: str, attributes: dict[str, Any]
    ) -> Any:
        """Write/update attributes on a model (e.g. the ``kg_intelligence`` blob)."""
        return self.request(
            "PUT",
            self.paths["model_attributes"].format(model_id=model_id),
            json={"attributes": attributes},
            content_type="application/json",
        )

    def set_object_attributes(
        self, object_id: str, attributes: dict[str, Any]
    ) -> Any:
        """Write/update attributes on a single object."""
        return self.request(
            "PUT",
            self.paths["object_attributes"].format(object_id=object_id),
            json={"attributes": attributes},
            content_type="application/json",
        )
