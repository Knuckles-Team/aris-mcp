# aris-mcp

Software AG **ARIS** REST API + MCP Server + A2A Server for Agentic AI.

`aris-mcp` connects the agent ecosystem to an ARIS tenant (ARIS Connect / ARIS
Enterprise / ARIS Cloud). It is the inbound *and* outbound bridge for the
agent-utilities Knowledge Graph's Camunda + ARIS ↔ KG integration:

- **Inbound** — the KG ARIS extractor (`enrichment/extractors/aris.py`) consumes
  this client to lift ARIS models + their EPC structure (functions → BusinessTask,
  rule operators → gateways, events collapsed, connections → FLOWS_TO) into the
  canonical ArchiMate ontology, where they reconcile with Camunda/Egeria via
  `ALIGNED_WITH` and are reasoned over in OWL/RDF.
- **Outbound** — the KG process-intelligence writeback (`enrichment/process_writeback.py`)
  uses `set_model_attributes` to write a `kg_intelligence` attribute back onto
  ARIS models (gated by `ARIS_ENABLE_WRITE`).

## Tools

| Tool | Actions |
|------|---------|
| `aris_model` | `list`, `get`, `objects`, `connections`, `attributes`, `set_attributes`¹ |
| `aris_object` | `set_attributes`¹ |

¹ writes require `ARIS_ENABLE_WRITE=True`.

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `ARIS_API_BASE` | ARIS REST base URL (tenant API root) | `http://localhost/abs/api` |
| `ARIS_SSL_VERIFY` | verify TLS | `True` |
| `ARIS_OAUTH_URL` / `ARIS_CLIENT_ID` / `ARIS_CLIENT_SECRET` / `ARIS_TENANT` | OAuth2 client-credentials (preferred) | — |
| `ARIS_TOKEN` | static bearer token (alt to OAuth) | — |
| `ARIS_USERNAME` / `ARIS_PASSWORD` | HTTP basic (alt) | — |
| `ARIS_PATHS_JSON` | JSON overriding REST path templates per tenant | — |
| `ARIS_ENABLE_WRITE` | allow attribute writes | `False` |

> **Tenant differences.** ARIS deployments vary (Connect ABS portal vs the public
> ARIS API; on-prem vs Cloud). The defaults follow the common ARIS Connect ABS
> REST layout. If your tenant's paths differ, set `ARIS_PATHS_JSON`, e.g.
> `{"models":"v2/repository/models","model_objects":"v2/models/{model_id}/objects"}`.

## Run

```bash
pip install .[all]
aris-mcp                       # stdio (default)
aris-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

## Deployment

1. **stdio** — `uv run aris-mcp` (see `mcp_config.json`).
2. **streamable-http** — `aris-mcp --transport streamable-http --port 8000`.
3. **local container** — build from `docker/` and run with the env above.
4. **remote** — point your client at `http://aris-mcp.arpa/mcp`.


<!-- BEGIN agent-os-genesis-deploy (generated; do not edit between markers) -->

## Deploy with `agent-os-genesis`

This package can be provisioned for you — skill-guided — by the **`agent-os-genesis`**
universal skill (its *single-package deploy mode*): it picks your install method, seeds
secrets to OpenBao/Vault (or `.env`), trusts your enterprise CA, registers the MCP
server, and verifies it — the same machinery that stands up the whole Agent OS, narrowed
to just this package. Ask your agent to **"deploy `aris-mcp` with agent-os-genesis"**.

| Install mode | Command |
|------|---------|
| Bare-metal, prod (PyPI) | `uvx aris-mcp` · or `uv tool install aris-mcp` |
| Bare-metal, dev (editable) | `uv pip install -e ".[all]"` · or `pip install -e ".[all]"` |
| Container, prod | deploy `knucklessg1/aris-mcp:latest` via docker-compose / swarm / podman / podman-compose / kubernetes |
| Container, dev (editable) | deploy `docker/compose.dev.yml` (source-mounted at `/src`; edits live on restart) |

Secrets are read-existing + seeded via `vault_sync` — you are only prompted for what's missing.

<!-- END agent-os-genesis-deploy -->
