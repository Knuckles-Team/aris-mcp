# CONN-ARIS-MCP — Implementation plan

Governing spec: [spec.md](spec.md). Rows: [requirements.md](requirements.md).

## Summary

A source resolver serves the live tenant, an AML directory or the bundled fixture repository behind one read interface and refuses with typed codes when unconfigured. A safe AML reader and writer produce the live client's record shapes. An adapter converts EPC records to and from the canonical workflow, driven by the ontology annotations. The action routers are replaced by one typed tool per operation.

## Technical Context

- **Language/Version**: Python 3.14 (floor 3.12)
- **Primary Dependencies**: scion-sdk, fastmcp, defusedxml
- **Storage**: N/A; the connector stores nothing
- **Testing**: pytest; the proof level each row names
- **Target Platform**: Linux containers
- **Project Type**: connector (MCP server)
- **Performance Goals**: N/A
- **Constraints**: one tool per operation; shared capabilities come from the SDK; no external parser for untrusted XML beyond defusedxml
- **Scale/Scope**: 8 rows

## Constitution Check

- One owner per concept: pass. The connector owns one external system's calls, mappings and tools; the canonical workflow and the agent workflow graph stay with the engine.
- Connectors depend on the SDK and are called through arbora: pass.
- No ratchets: pass. The rows add no suppression.

## Project Structure

```text
aris_mcp/source.py  new
aris_mcp/aml.py  new
aris_mcp/canonical.py  new
aris_mcp/vocabulary.py  new
aris_mcp/fixtures/repository/  new
aris_mcp/mcp/mcp_aris.py  existing
aris_mcp/mcp_server.py  existing
aris_mcp/auth.py  existing
aris_mcp/__init__.py  existing
aris_mcp/connector_sources.py  existing
aris_mcp/ontology/mappings/source.yaml  existing
tests/fixtures/  new
tests/bpmn_reference.py  new (test-only)
```

## Phase 0: Research

No unknowns. The canonical wire form, ids, digest, EPC mapping and loss rules are the engine's contract.

## Phase 1: Design

### Source resolution (R001, R006)

`resolve_mode` reads `ARIS_API_BASE` and `ARIS_REPOSITORY_DIR` only. `get_source` returns the live client or a cached `FileRepository` that answers the live client's read methods from AML; writes on it refuse `ARIS_READ_ONLY_SOURCE`. `ArisRefusal` subclasses fastmcp `ToolError`, so every tool raises the same JSON body; the SDK error middleware delivers it to the client as the call's error with that body in its message.

### AML (R002, R003)

The reader parses with defusedxml (`forbid_dtd=True`, entities and external references refused) after a 16 MiB size check, resolves occurrences to definitions and connection occurrences to their source and target definitions. The writer builds the same structure with the standard library and re-reads to the same records.

### Canonical adapter (R004, R005, R008)

`epc_to_canonical` classifies control objects with the ontology vocabulary, folds intermediate events, splits a join-and-split operator, numbers the steps (Kahn with the contract key) and computes the digest. `canonical_to_epc` maps each step back, merges a join-then-split pair from one source element into one operator, restores the annex on a same-source export and records losses; `strict` refuses. A test-only BPMN reference reader proves the cross-source fixture.

### Tools (R007)

`register_aris_tools` registers fifteen typed tools and the contracts resource; the `Connector` declares no `api`, so the SDK generates no operation tools.

## Phase 2: Task approach

`tasks.md` holds one task line per row, producer first.

## Complexity Tracking

None. The constitution check passed.

## Build contract

The repository pre-commit hooks apply: `ruff-format`, `connector-standard`, `secrets`, `tests-fast`. Each row names its proving test. No suppression and no duplicate implementation.

## Production caller chain

1. `CONN-ARIS-MCP-R001`: `scion_sdk.cli:serve` -> `aris_mcp:connector` (`aris_mcp/__init__.py`) -> `extra_registrations` `source.log_resolved_mode`; each repository tool in `aris_mcp/mcp/mcp_aris.py` -> `source.get_source` -> `auth.get_client` or `source.FileRepository`.
2. `CONN-ARIS-MCP-R002`: `aris_import_aml` / `aris_export_canonical_workflow` / `FileRepository.__init__` -> `aml.read_aml`.
3. `CONN-ARIS-MCP-R003`: `aris_export_aml` / `aris_import_canonical_workflow` -> `aml.write_aml`.
4. `CONN-ARIS-MCP-R004`: `aris_export_canonical_workflow` -> `canonical.epc_to_canonical` -> `vocabulary.vocabulary`.
5. `CONN-ARIS-MCP-R005`: `aris_import_canonical_workflow` -> `canonical.canonical_to_epc`.
6. `CONN-ARIS-MCP-R006`: `source.get_source` (`ARIS_REPOSITORY_DIR=fixture`) -> `FileRepository(fixture_dir())`.
7. `CONN-ARIS-MCP-R007`: `aris_mcp:connector` (`tools="aris_mcp.mcp_server"`) -> `register_aris_tools`.
8. `CONN-ARIS-MCP-R008`: `canonical.epc_to_canonical` over `tests/fixtures/invoice-approval.aml`.

## Cross-repo seams

none. The canonical workflow (`medulla.process.canonical/v1`), its native BPMN reader and the agent workflow graph are the engine's; this connector produces and consumes the wire form. The equivalence fixture files are copied to the engine's fixture directory.
