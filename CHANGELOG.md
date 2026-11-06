# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-11-06

### Changed
- One typed tool per operation replaces the `aris_model` / `aris_object` action
  routers and `aris_ingest_models`: `aris_list_models`, `aris_get_model`,
  `aris_list_model_objects`, `aris_list_model_connections`,
  `aris_get_model_attributes`, `aris_set_model_attributes`,
  `aris_set_object_attributes`, `aris_ingest_model_inventory`,
  `aris_ingest_model_graph`, `aris_ingest_model_export`.
- `ARIS_API_BASE` has no default any more (it targeted `http://localhost/abs/api`).
  Without it and without `ARIS_REPOSITORY_DIR` the server still starts and every
  repository tool refuses `ARIS_NOT_CONFIGURED` with a remedy. Refusals are
  returned as an `isError` tool result whose structured content is
  `{refused: true, code, message, remedy}`.
- Ontology hard cutover: `:EPCObject`, `:EPCFunction`, `:EPCEvent`, `:EPCRule` and
  `:ProcessConnection` are gone. Pack classes are leaves of the core `:EpcFunction`,
  `:EpcRuleOperator` and `:ProcessEventType` (`:EpcHumanFunction`,
  `:EpcAutomatedFunction`, `:EpcDecisionFunction`, `:EpcProcessInterface`,
  `:EpcStartEvent`, `:EpcEndEvent`, `:EpcIntermediateEvent`, `:EpcAndOperator`,
  `:EpcOrOperator`, `:EpcXorOperator`), plus attachment classes, `:EpcModel` and
  `:EpcConnection`; annotations `:dagNodeKind`, `:canonicalGateKind`,
  `:arisTypeNum`, `:arisSymbolNum`, `:epcAttachmentRole`, `:executedByTool`. The KG
  ingest types nodes by TypeNum/SymbolNum and always reifies connections.
- Require `scion-sdk>=0.8.2,<0.9.0` and `defusedxml`; `uv.lock` relocked.

### Added
- Offline sources: `ARIS_REPOSITORY_DIR=<dir>` serves a directory of AML exports
  read-only; `ARIS_REPOSITORY_DIR=fixture` serves the bundled sample repository.
  `aris_get_source_status` reports the mode.
- Safe AML reader and writer; `aris_import_aml`, `aris_export_aml`.
- EPC <-> canonical workflow (`medulla.process.canonical/v1`):
  `aris_export_canonical_workflow`, `aris_import_canonical_workflow` (with
  `strict` loss refusal `PROCESS_EXPORT_LOSSY`).
- Tool-use contracts served as `ontology://aris-mcp/contracts.ttl`; agent prompts
  `aris-process-operator` and `aris-process-modeler`; skill
  `aris-epc-to-canonical-workflow`.

## [1.3.8] - 2026-10-30

### Changed
- Require `scion-sdk>=0.6.4,<0.7.0`; `uv.lock` relocked.

## [1.3.6] - 2026-10-27

### Added
- Packaged `aris-mcp-development` skill documenting the connector's rapid-delivery,
  runtime, security, package, and release contracts.

## [1.3.5] - 2026-10-24

### Changed
- Central connector migration: requires `agent-connector-sdk>=0.5.4`; server bootstrap, version, containers, ontology artifacts, security scaffold and pre-commit config are provided centrally.

## [Unreleased]

### Added

- Initial `aris-mcp` package: Software AG ARIS REST API client + FastMCP server + A2A server.
  - Read tools (`aris_model`/`aris_object`): `list_models`, `list_model_objects`,
    `list_model_connections`, `list_model_attributes`.
  - Gated write tools (`set_model_attributes`, `set_object_attributes`) behind the
    `ARIS_ENABLE_WRITE` flag.
  - Configurable ARIS REST layout via `ARIS_PATHS_JSON`; OAuth2 client-credentials,
    bearer, and basic auth support.
  - Inbound bridge for the agent-utilities KG ARIS extractor and outbound bridge for
    process-intelligence writeback (ArchiMate ontology reconciliation with Camunda/Egeria).
