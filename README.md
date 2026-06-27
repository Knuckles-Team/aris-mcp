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

## Available MCP Tools

The table below is auto-generated from the live server — do not edit by hand.

<!-- MCP-TOOLS-TABLE:START -->

#### Condensed action-routed tools (default — `MCP_TOOL_MODE=condensed`)

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `aris_model` | `ARISTOOL` | Work with ARIS models and their EPC structure. |
| `aris_object` | `ARISTOOL` | Write attributes on a single ARIS object. |

#### Verbose 1:1 API-mapped tools (`MCP_TOOL_MODE=verbose` or `both`)

<details>
<summary>7 per-operation tools — one per public API method (click to expand)</summary>

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `aris_get_model` | `ARIS_APITOOL` | Get a single model's metadata (including its attributes). |
| `aris_list_model_attributes` | `ARIS_APITOOL` | Get a model's attributes (used for writeback idempotency read-back). |
| `aris_list_model_connections` | `ARIS_APITOOL` | List the directed control-flow connections between a model's objects. |
| `aris_list_model_objects` | `ARIS_APITOOL` | List the EPC objects (functions/events/rule operators) of a model. |
| `aris_list_models` | `ARIS_APITOOL` | List models in the tenant/database (process + architecture). |
| `aris_set_model_attributes` | `ARIS_APITOOL` | Write/update attributes on a model (e.g. the ``kg_intelligence`` blob). |
| `aris_set_object_attributes` | `ARIS_APITOOL` | Write/update attributes on a single object. |

</details>

_2 action-routed tool(s) (default) · 7 verbose 1:1 tool(s). Each is enabled unless its `<DOMAIN>TOOL` toggle is set false; `MCP_TOOL_MODE` selects the surface (`condensed` default · `verbose` 1:1 · `both`). Auto-generated — do not edit._
<!-- MCP-TOOLS-TABLE:END -->

> Writes require `ARIS_ENABLE_WRITE=True`.

## Environment Variables

<!-- ENV-VARS-TABLE:START -->

#### Package environment variables

| Variable | Example | Description |
|----------|---------|-------------|
| `ARIS_API_BASE` | `http://localhost/abs/api` | ARIS REST base URL (tenant API root). Default follows the ARIS Connect ABS layout. |
| `ARIS_SSL_VERIFY` | `True` | Verify TLS (set False for self-signed / homelab tenants) |
| `ARIS_OAUTH_URL` | — | 1. OAuth2 client-credentials (preferred for ARIS Cloud / Connect) |
| `ARIS_CLIENT_ID` | — |  |
| `ARIS_CLIENT_SECRET` | — |  |
| `ARIS_TENANT` | — |  |
| `ARIS_TOKEN` | — | 2. Static bearer token (alternative to OAuth) |
| `ARIS_USERNAME` | — | 3. HTTP basic auth (alternative) |
| `ARIS_PASSWORD` | — |  |
| `ARIS_PATHS_JSON` | — | e.g. {"models":"v2/repository/models","model_objects":"v2/models/{model_id}/objects"} |
| `ARIS_ENABLE_WRITE` | `False` | Allow (gated) attribute writes back onto ARIS models (KG writeback) |
| `TRANSPORT` | `stdio` | stdio, streamable-http, or sse |
| `HOST` | `0.0.0.0` |  |
| `PORT` | `8000` |  |
| `MCP_TOOL_MODE` | `condensed` | Tool surface: condensed, verbose, or both |
| `MCP_ENABLED_TOOLS` | — | Comma-separated tool / tag allow/deny lists |
| `MCP_DISABLED_TOOLS` | — |  |
| `MCP_ENABLED_TAGS` | — |  |
| `MCP_DISABLED_TAGS` | — |  |
| `DEBUG` | `False` |  |
| `PYTHONUNBUFFERED` | `1` |  |
| `ARISTOOL` | `True` | The action-routed ARIS tools (aris_model, aris_object) share this toggle. |
| `ENABLE_OTEL` | `True` |  |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — |  |
| `OTEL_EXPORTER_OTLP_PUBLIC_KEY` | — |  |
| `OTEL_EXPORTER_OTLP_SECRET_KEY` | — |  |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | — |  |
| `EUNOMIA_TYPE` | `none` |  |
| `EUNOMIA_POLICY_FILE` | `mcp_policies.json` |  |
| `EUNOMIA_REMOTE_URL` | — |  |

#### Inherited agent-utilities variables (apply to every connector)

| Variable | Example | Description |
|----------|---------|-------------|
| `MCP_CLIENT_AUTH` | — | Outbound MCP auth (`oidc-client-credentials` for fleet calls) |
| `OIDC_CLIENT_ID` | — | OIDC client id (service-account auth) |
| `OIDC_CLIENT_SECRET` | — | OIDC client secret (service-account auth) |
| `MCP_URL` | `http://localhost:8000/mcp` | URL of the MCP server the agent connects to |
| `PROVIDER` | `openai` | LLM provider for the agent |
| `MODEL_ID` | `gpt-4o` | Model id for the agent |
| `ENABLE_WEB_UI` | `True` | Serve the AG-UI web interface |

_30 package + 7 inherited variable(s). Auto-generated from `.env.example` + the shared agent-utilities set — do not edit._
<!-- ENV-VARS-TABLE:END -->


Every variable the server reads, grouped by concern.

### Connection & Credentials
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

### MCP server / transport
| Variable | Description | Default |
|----------|-------------|---------|
| `TRANSPORT` | `stdio`, `streamable-http`, or `sse` | `stdio` |
| `HOST` | Bind host (HTTP transports) | `0.0.0.0` |
| `PORT` | Bind port (HTTP transports) | `8000` |
| `MCP_TOOL_MODE` | Tool surface: `condensed`, `verbose`, or `both` | `condensed` |
| `MCP_ENABLED_TOOLS` / `MCP_DISABLED_TOOLS` | Comma-separated tool allow/deny list | — |
| `MCP_ENABLED_TAGS` / `MCP_DISABLED_TAGS` | Comma-separated tag allow/deny list | — |
| `DEBUG` | Verbose logging | `False` |
| `PYTHONUNBUFFERED` | Unbuffered stdout (recommended in containers) | `1` |

### Tool toggles
The action-routed tools can be disabled via their toggle env var (set to `false`):
`ARISTOOL` (see the [Available MCP Tools](#available-mcp-tools) table above).

### Telemetry & governance
| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_OTEL` | Enable OpenTelemetry export | `True` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint | — |
| `OTEL_EXPORTER_OTLP_PUBLIC_KEY` / `OTEL_EXPORTER_OTLP_SECRET_KEY` | OTLP auth keys | — |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | OTLP protocol (e.g. `http/protobuf`) | — |
| `EUNOMIA_TYPE` | Authorization mode: `none`, `embedded`, `remote` | `none` |
| `EUNOMIA_POLICY_FILE` | Embedded policy file | `mcp_policies.json` |
| `EUNOMIA_REMOTE_URL` | Remote Eunomia server URL | — |

### Agent CLI (full `[agent]` runtime only)
| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_URL` | URL of the MCP server the agent connects to | `http://localhost:8000/mcp` |
| `PROVIDER` | LLM provider (e.g. `openai`) | `openai` |
| `MODEL_ID` | Model id (e.g. `gpt-4o`) | `gpt-4o` |
| `ENABLE_WEB_UI` | Serve the AG-UI web interface | `True` |

## Installation

> **Install the slim `[mcp]` extra.** Install `aris-mcp[mcp]` — the MCP-server extra
> that pulls only the FastMCP / FastAPI tooling (`agent-utilities[mcp]`). It deliberately
> **excludes** the heavy agent runtime (the epistemic-graph engine, `pydantic-ai`,
> `dspy`, `llama-index`, `tree-sitter`), so `uvx`/container installs are dramatically
> smaller and faster. Use the full `[agent]` extra only when you need the integrated
> Pydantic AI agent.

Pick the extra that matches what you want to run:

| Extra | Installs | Use when |
|-------|----------|----------|
| `aris-mcp[mcp]` | Slim MCP server only (`agent-utilities[mcp]` — FastMCP/FastAPI) | You only run the **MCP server** (smallest install / image) |
| `aris-mcp[agent]` | Full agent runtime (`agent-utilities[agent,logfire]` — Pydantic AI + the epistemic-graph engine) | You run the **integrated agent** |
| `aris-mcp[all]` | Everything (`mcp` + `agent` + `logfire`) | Development / both surfaces |

```bash
# MCP server only (recommended for tool hosting — slim deps)
uv pip install "aris-mcp[mcp]"

# Full agent runtime (Pydantic AI + epistemic-graph engine)
uv pip install "aris-mcp[agent]"

# Everything (development)
uv pip install "aris-mcp[all]"      # or: python -m pip install "aris-mcp[all]"
```

### Container images (`:mcp` vs `:agent`)

One multi-stage `docker/Dockerfile` builds two right-sized images, selected by `--target`:

| Image tag | Build target | Contents | Entrypoint |
|-----------|--------------|----------|------------|
| `knucklessg1/aris-mcp:mcp` | `--target mcp` | `aris-mcp[mcp]` — **slim**, no engine/`pydantic-ai`/`dspy`/`llama-index`/`tree-sitter` | `aris-mcp` |
| `knucklessg1/aris-mcp:latest` | `--target agent` (default) | `aris-mcp[agent]` — **full** agent runtime + epistemic-graph engine | `aris-agent` |

```bash
docker build --target mcp   -t knucklessg1/aris-mcp:mcp    docker/   # slim MCP server
docker build --target agent -t knucklessg1/aris-mcp:latest docker/   # full agent
```

`docker/mcp.compose.yml` runs the slim `:mcp` server; `docker/agent.compose.yml` runs the
agent (`:latest`) with a co-located `:mcp` sidecar.

### Knowledge-graph database (`epistemic-graph`)

The **full agent** (`[agent]` / `:latest`) embeds the **epistemic-graph** engine (pulled in
transitively via `agent-utilities[agent]`). For production — or to share one knowledge graph
across multiple agents — run **epistemic-graph as its own database container** and point the
agent at it instead of embedding it. Deployment recipes (single-node + Raft HA), connection
config, and the full database architecture (with diagrams) are documented in the
[epistemic-graph deployment guide](https://knuckles-team.github.io/epistemic-graph/deployment/).
The slim `[mcp]` server does **not** require the database.

## Run

```bash
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
