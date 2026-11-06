# Architecture Overview

This package splits into three clear tiers:
1. **API Layer**: `api/` folder contains the granular `ArisApi` REST client covering model inventory, EPC objects, connections, and attribute operations.
2. **MCP Layer**: `mcp/` registers one typed FastMCP tool per operation over the source resolved by `source.py` (live client, AML directory or fixture repository); `aml.py` and `canonical.py` read/write AML and convert EPC to and from the canonical workflow.
3. **Agent Layer**: Exposes a graph-based autonomous Pydantic AI agent via `agent_server.py`.
