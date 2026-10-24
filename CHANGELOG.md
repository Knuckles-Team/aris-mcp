# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
