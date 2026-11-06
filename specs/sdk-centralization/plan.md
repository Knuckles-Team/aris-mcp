# CONN-ARIS-MCP-SDK-CENTRALIZATION — Implementation plan

Governing spec: [spec.md](spec.md). Rows: [requirements.md](requirements.md).

## Summary

The SDK owns the capability rows cited in [requirements.md](requirements.md). The connector adds no transport code of its own. The connector builds on the SDK. HTTP goes through the SDK governed client, and TLS comes from `resolve_tls_profile` for the connector's settings prefix.

## Technical Context

- **Language/Version**: Python 3.14 (floor 3.12)
- **Primary Dependencies**: scion-sdk, fastmcp
- **Storage**: N/A; the connector stores nothing
- **Testing**: pytest; the proof level each row names
- **Target Platform**: Linux containers
- **Project Type**: connector (MCP server)
- **Performance Goals**: N/A
- **Constraints**: one tool per API operation; shared capabilities come from the SDK
- **Scale/Scope**: 5 rows

## Constitution Check

- One owner per concept: pass. The connector owns one external system's calls, mappings and tools only.
- Connectors depend on the SDK and are called through arbora: pass.
- No ratchets: pass. The rows add no suppression.

## Project Structure

```text
aris_mcp/api/api_client_base.py  existing
aris_mcp/mcp/mcp_aris.py  existing
tests/test_sdk_transport.py  existing
```

## Phase 0: Research

No unknowns. Each row names the code it touches.

## Phase 1: Design

### Interfaces and data model

No tool, argument or result changes.

### Live integration path

Every tool reaches ARIS through the connector client, which sends each request through the SDK.

### Quality and release gates

The focused tests in [test-spec.md](test-spec.md) must pass. The SDK floor must be the latest published release.

### Risks, alternatives, and decisions

A private certificate authority must be supplied through the TLS profile. A flag that disables verification must not return.

## Phase 2: Task approach

`tasks.md` holds one task line per row, producer first.

## Complexity Tracking

None. The constitution check passed.

## Build contract

The repository pre-commit hooks apply: `ruff-format`, `connector-standard`, `secrets`, `tests-fast`. Each row names its proving test. No suppression and no duplicate implementation.

## Production caller chain

1. `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.1`: The `aris-mcp` console script runs `scion_sdk.cli:serve`, which loads `aris_mcp/__init__.py::connector` (tools=`aris_mcp.mcp.mcp_aris`) builds `ArisApi` through `aris_mcp/auth.py::get_client`; `ApiClientBase.__init__` in `aris_mcp/api/api_client_base.py` calls `build_http_client`, which wraps `scion_sdk.http.client.create_http_client`, and `auth.py::_fetch_oauth_token` uses the same builder.
2. `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.2`: The `aris-mcp` console script runs `scion_sdk.cli:serve`, which loads `aris_mcp/__init__.py::connector` (tools=`aris_mcp.mcp.mcp_aris`) builds `ArisApi` through `aris_mcp/auth.py::get_client`; `get_client` resolves the profile with `resolve_tls_profile` and passes it to `_fetch_oauth_token` (line 16) and to `ArisApi`.
3. `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.3`: The `aris-mcp` console script runs `scion_sdk.cli:serve`; the read and write tools in `aris_mcp/mcp/mcp_aris.py` (`aris_list_models`, `aris_get_model`, `aris_list_model_objects`, `aris_list_model_connections`, `aris_set_model_attributes`, `aris_set_object_attributes`) call `ArisApi.list_models`, `get_model`, `list_model_objects` and `list_model_connections`, which call `aris_mcp/api/api_client_base.py::ApiClientBase.request` (line 94).
4. `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.4`: Installing the package resolves `dependencies` in pyproject.toml; the `aris-mcp` console script (`scion_sdk.cli:serve`) then imports `scion_sdk.http.client` and `scion_sdk.tls.resolve` used by `aris_mcp/api/api_client_base.py`.

## Cross-repo seams

none. The cited owner rows are library capabilities the connector calls in process; spec.md names them.
