"""Public client facade for aris_mcp.

Exposes a single :class:`ArisApi` REST client. Kept as a thin facade (mirroring
``camunda_mcp.api_client.Api``) so the package shape matches the connector fleet
and a future second ARIS surface can be added without changing callers.
"""

from aris_mcp.api.api_client_aris import ArisApi

__version__ = "0.1.1"

__all__ = ["ArisApi"]
