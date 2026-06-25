# Architecture Overview

This package splits into three clear tiers:
1. **API Layer**: `api/` folder contains the granular `ArisApi` REST client covering model inventory, EPC objects, connections, and attribute operations.
2. **MCP Layer**: `mcp/` registers FastMCP tools (`aris_model`, `aris_object`) invoking the API client under semantic tags.
3. **Agent Layer**: Exposes a graph-based autonomous Pydantic AI agent via `agent_server.py`.
