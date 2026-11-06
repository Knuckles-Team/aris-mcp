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
- **Scale/Scope**: 6 rows

## Constitution Check

- One owner per concept: pass. The connector owns one external system's calls, mappings and tools only.
- Connectors depend on the SDK and are called through arbora: pass.
- No ratchets: pass. The rows add no suppression.

## Project Structure

```text
pyproject.toml  existing
aris_mcp/__init__.py  existing
aris_mcp/api/api_client_aris.py  existing
aris_mcp/ontology/aris.ttl  existing
aris_mcp/vocabulary.py  new
aris_mcp/kg_ingest.py  existing
aris_mcp/skills/  existing
aris_mcp/prompts/  new
aris_mcp/_surface.py  new
aris_mcp/connector_contracts.py  new
```

## Phase 0: Research

No unknowns. Each row names the code it touches.

## Phase 1: Design

The rows are delivered in place; the design is the caller chain below.

### EPC ontology, skills, prompts and contracts (R003 to R006)

The ontology is the source of truth of the EPC to canonical mapping: `vocabulary.py` parses the class blocks of `aris.ttl` (the subset of Turtle the file uses) into type, symbol, kind, gate and attachment-role lookups that `canonical.py` and the KG ingest use. Pack classes are leaves of the core `:EpcFunction`, `:EpcRuleOperator` and `:ProcessEventType`; the pack declares no core term. Contracts, links, locations and roles are plain declarations rendered to Turtle by `_surface.py`; prompts and skills are packaged content the SDK serves.

## Phase 2: Task approach

`tasks.md` holds one task line per row, producer first.

## Complexity Tracking

None. The constitution check passed.

## Build contract

The repository pre-commit hooks apply: `ruff-format`, `connector-standard`, `secrets`, `tests-fast`. Each row names its proving test. No suppression and no duplicate implementation.

## Production caller chain

1. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001`: The `aris-mcp` console script in pyproject.toml runs `scion_sdk.cli:serve`, which loads the `scion_sdk.connector` entry point `aris-mcp = aris_mcp:connector` and builds the server from `aris_mcp/__init__.py::connector`.
2. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002`: (planned) The `aris-mcp` console script runs `scion_sdk.cli:serve` and loads `aris_mcp/__init__.py::connector`; arbora calls the existing read tools `aris_mcp/mcp/mcp_aris.py::register_aris_tools.aris_list_model_objects` and `aris_list_model_connections` through `fleet.call`, which reads `ArisApi.list_model_objects` and `list_model_connections` in `aris_mcp/api/api_client_aris.py`.

3. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003`: the SDK serves `aris_mcp/ontology/aris.ttl` as `ontology://aris-mcp/aris.ttl`; `aris_export_canonical_workflow` (`aris_mcp/mcp/mcp_aris.py`) -> `canonical.epc_to_canonical` -> `vocabulary.vocabulary()`; `aris_ingest_model_graph` -> `kg_ingest.ingest_model_graph` -> `canonical.classify_epc_objects`.
4. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004`: the SDK content registrar serves `aris_mcp/skills/*/SKILL.md` as `skill://` resources.
5. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005`: the SDK content registrar serves `aris_mcp/prompts/*.json` as prompts; `mcp_aris.contracts_turtle` reads each prompt's `agent` object.
6. `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006`: `register_aris_tools` registers `ontology://aris-mcp/contracts.ttl` -> `contracts_turtle()` -> `_surface.render_surface_turtle` over `connector_contracts.CONTRACTS`, `LINKS`, `LOCATIONS`, `ROLES`.

## Cross-repo seams

none. The pack classes are leaves of core terms owned by the engine (`MEDULLA-CQ-CONN-R072.1`); `:dagNodeKind` and `:canonicalGateKind` are core annotation properties the engine specifies; they are declared here with the same IRIs. The cited owner rows are library capabilities the connector calls in process; spec.md names them.
