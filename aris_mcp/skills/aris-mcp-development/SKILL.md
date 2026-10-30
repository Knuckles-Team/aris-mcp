---
name: aris-mcp-development
skill_type: skill
description: >-
  Develop and maintain the Software AG ARIS connector while preserving its
  Connector boundary, REST client contract, authentication policy, KG source
  declarations, package contents, and release evidence.
license: MIT
tags: [aris, connector, mcp, sdk, development]
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---
# ARIS MCP Development

This is the repository development skill for `aris-mcp`. The owning delivery
row is `PIPE-CONNSPEC-R104.4`; use this skill together with the repository
`AGENTS.md`, the relevant connector specification, and the focused tests.

## Repository and runtime map

- `aris_mcp/__init__.py` declares the one SDK `Connector`, including the
  `ArisApi` client, `get_client` factory, tool registrar module, and connector
  instructions.
- `aris_mcp/api/api_client_aris.py` is the thin ARIS REST facade. Keep the
  stable model, object, connection, attribute, and export method contracts.
- `aris_mcp/auth.py` builds the client from OAuth2 client credentials, a bearer
  token, or HTTP basic authentication and resolves the shared TLS profile.
- `aris_mcp/mcp/mcp_aris.py` registers the `aris_model`, `aris_object`,
  `aris_ingest_models`, and `aris_ingest_model_export` tools. Attribute writes
  remain gated by `ARIS_ENABLE_WRITE`.
- `aris_mcp/connector_sources.py` is the live `aris-models` source and its
  ProcessModel, EPC, connection, and model-export schema declarations.
- `aris_mcp/skills/**` is included in the packaged connector data. A skill
  change therefore needs a package-content check before publication.
- `pyproject.toml` exposes the `aris-mcp` console script through
  `scion_sdk.cli:serve` and registers the `aris-mcp` SDK connector
  entry point for `aris_mcp:connector`.

## Connection and security contract

`ARIS_API_BASE` selects the REST root. OAuth2 uses `ARIS_OAUTH_URL`,
`ARIS_CLIENT_ID`, `ARIS_CLIENT_SECRET`, and optionally `ARIS_TENANT`; a static
`ARIS_TOKEN` or `ARIS_USERNAME`/`ARIS_PASSWORD` is an alternative auth path.
`ARIS_TLS_PROFILE` and `ARIS_TLS_PROFILE_REF` select the shared verified TLS
policy. `ARIS_PATHS_JSON` can override tenant-specific REST path templates.
TLS verification stays enabled, and credentials belong in injected environment
secrets. `ARIS_ENABLE_WRITE` defaults to false and must remain an explicit
writeback gate.

## Rapid delivery: the 5-minute contract

1. Read the owning spec row, this skill, `AGENTS.md`, and the focused tests
   before changing a connector surface.
2. Inspect the active `Connector`, tool registrar and action maps, REST client,
   authentication/TLS setup, source declarations, and package-data rules.
3. Make the smallest connector-owned change. Preserve public tool names,
   action names, payloads, endpoint path overrides, authentication choices,
   TLS verification, ontology/source identifiers, and the SDK `Connector`
   boundary.
4. Run the directly bound tests with `uv run --locked --extra test pytest`,
   then run the repository hooks. Use the approved narrow test wrapper when
   the delivery lane requires it; never bypass a hook or a failing gate.
5. If package code or package content changes, update the package and lockfile
   through the repository's normal release process. Inspect the built wheel
   and sdist for the intended `aris_mcp/skills/**` content before publication.
6. Treat Pages as separate evidence: after the exact main commit publishes,
   verify the successful Pages revision and probe `/spec-delivery/`,
   `/spec-delivery/index.html`, and its `snapshot.json`. Record the revision
   before making a delivery claim.

## Focused validation

For a tool or client change, exercise the smallest relevant test file and keep
the read-first and write-gated paths distinct. Include tenant path overrides,
auth/TLS selection, source declarations, or KG ingestion only when the change
touches those contracts. For a skill or package-data change, verify the skill
frontmatter, required headings, and wheel/sdist contents without importing a
live ARIS tenant.

Use the normal commands from `AGENTS.md`:

```bash
uv sync --locked
uv run --locked --extra test pytest -q tests/<focused-test>.py
uvx pre-commit run --all-files
```

## Publication and Pages

`.github/workflows/pipeline.yml` delegates package publication to
`Knuckles-Team/pipelines/.github/workflows/python_pipeline.yml@main` with
`connector: true`, then invokes
`Knuckles-Team/pipelines/.github/workflows/container_pipeline.yml@main` with
`render_connector: true`. `.github/workflows/pages.yml` delegates documentation
and the spec dashboard to `pages_pipeline.yml@main`. Keep these shared caller
contracts and their main-branch triggers intact. Generated spec status belongs
to Pipelines; do not hand-edit central status or promote a rollup from a
connector change.

Never place credentials, tenant data, generated release artifacts, or bypass
instructions in a skill. Keep a commit focused on the owning row and cite it
with `Spec: PIPE-CONNSPEC-R104.4` when this development skill is changed.
