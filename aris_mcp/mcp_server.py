"""Main FastMCP server and tool registration for aris-mcp."""

from aris_mcp.mcp.mcp_aris import register_aris_tools  # noqa: F401

# SDK discovery registers the register_<tag>_tools functions bound in this module.
__all__ = ["register_aris_tools"]
