# CONN-ARIS-MCP-CONNECTOR-CONTENT — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Architecture

`pyproject.toml` declares `aris-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `aris_mcp` from it.
