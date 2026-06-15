# aris-mcp - AGENTS

> Claude Code loads this file via `CLAUDE.md` (`@AGENTS.md` import) — the two stay
> in sync. Edit **this** file, not `CLAUDE.md`.

## Project Structure
- `aris_mcp/`: server code (`api/` REST client, `mcp/` thin tools, `auth.py`, `mcp_server.py`, `agent_server.py`)
- `tests/`: test suite
- `mcp_config.json`: connection template

## Tech Stack
- Python 3.11+
- agent-utilities >= 0.49.0
- requests (ARIS REST API, OAuth2/bearer/basic)
- Model Context Protocol (MCP) via FastMCP

## Commands
- `pytest`: run tests
- `pre-commit run --all-files`: lint

## Design notes
- The client is a **thin** REST wrapper; all logic stays in the agent-utilities KG
  extractor/writeback. Method names (`list_models`, `list_model_objects`,
  `list_model_connections`, `set_model_attributes`) are the contract the KG
  extractor probes — keep them stable.
- Endpoint **paths are configurable** (`ARIS_PATHS_JSON`) because ARIS tenants
  differ; only the paths move, never the method names.
- Writes are gated by `ARIS_ENABLE_WRITE` (default off).

## Quality Bar
Run `pre-commit run --all-files` and drive it fully green before committing. Do
not silence checks to force green. Never commit secrets.
