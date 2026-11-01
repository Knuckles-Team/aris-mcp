# CONN-ARIS-MCP-CONNECTOR-CONTENT — Implementation plan

Governing spec: [spec.md](spec.md). Rows: [requirements.md](requirements.md).

## Summary

`pyproject.toml` declares `aris-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `aris_mcp` from it.

## Technical Context

- **Language/Version**: Python 3.14 (floor 3.12)
- **Primary Dependencies**: scion-sdk, fastmcp
- **Storage**: N/A; the connector stores nothing
- **Testing**: pytest; the proof level each row names
- **Target Platform**: Linux containers
- **Project Type**: connector (MCP server)
- **Performance Goals**: N/A
- **Constraints**: one tool per API operation; shared capabilities come from the SDK
- **Scale/Scope**: 2 rows

## Constitution Check

- One owner per concept: pass. The connector owns one external system's calls, mappings and tools only.
- Connectors depend on the SDK and are called through arbora: pass.
- No ratchets: pass. The rows add no suppression.

## Project Structure

```text
pyproject.toml  existing
aris_mcp/__init__.py  existing
aris_mcp/api/api_client_aris.py  existing
```

## Phase 0: Research

No unknowns. Each row names the code it touches.

## Phase 1: Design

The rows are delivered in place; the design is the caller chain below.

## Phase 2: Task approach

`tasks.md` holds one task line per row, producer first.

## Complexity Tracking

None. The constitution check passed.

## Build contract

The repository pre-commit hooks apply: `ruff-format`, `connector-standard`, `secrets`, `tests-fast`. Each row names its proving test. No suppression and no duplicate implementation.

## Production caller chain

1. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001`: The `aris-mcp` console script in pyproject.toml runs `scion_sdk.cli:serve`, which loads the `scion_sdk.connector` entry point `aris-mcp = aris_mcp:connector` and builds the server from `aris_mcp/__init__.py::connector`.
2. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002`: (planned) The `aris-mcp` console script runs `scion_sdk.cli:serve` and loads `aris_mcp/__init__.py::connector`; arbora calls the existing read tool `aris_mcp/mcp/mcp_aris.py::register_aris_tools.aris_object` (line 72) through `fleet.call`, which reads `ArisApi.list_model_objects` and `list_model_connections` in `aris_mcp/api/api_client_aris.py`.

## Cross-repo seams

none. The cited owner rows are library capabilities the connector calls in process; spec.md names them.
