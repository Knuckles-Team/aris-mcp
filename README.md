# aris-mcp

Software AG **ARIS** REST API + MCP Server for Agentic AI.

`aris-mcp` connects the agent ecosystem to an ARIS tenant (ARIS Connect / ARIS
Enterprise / ARIS Cloud). It is the inbound *and* outbound bridge for the
agent-connector-sdk Knowledge Graph's Camunda + ARIS ↔ KG integration:

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

#### Intent tools

| MCP Tool | Kind | Description |
|----------|------|-------------|
| `aris_ingest_model_export` | intent | Store a raw ARIS model export (bytes) as a content-addressed KG blob. |
| `aris_ingest_models` | intent | Natively ingest ARIS models into epistemic-graph as typed nodes. |
| `aris_model` | intent | Work with ARIS models and their EPC structure. |
| `aris_object` | intent | Write attributes on a single ARIS object. |

_4 intent tool(s) · 0 operation(s). Call an operation as `act(action='<operation>', params={...})` (`ask` for reads); `find(action='describe', params={'action': '<operation>'})` returns its arguments. An operation is enabled unless its `<DOMAIN>TOOL` toggle is set false. Auto-generated — do not edit._
<!-- MCP-TOOLS-TABLE:END -->

> Writes require `ARIS_ENABLE_WRITE=True`.

## Environment Variables

<!-- ENV-VARS-TABLE:START -->

#### Package environment variables

| Variable | Example | Description |
|----------|---------|-------------|
| `ARIS_API_BASE` | `http://localhost/abs/api` | ARIS REST base URL (tenant API root). Default follows the ARIS Connect ABS layout. |
| `ARIS_TLS_PROFILE` | — | Named outbound TLS policy from AgentConfig (system trust store by default). Peer and hostname verification are mandatory and cannot be disabled. Point a self-signed / private-PKI tenant at its CA either with the standard SSL_CERT_FILE / SSL_CERT_DIR (applies to every service), or by naming a profile here (ARIS_TLS_PROFILE=<name>) resolved from a TLS_PROFILES / TLS_PROFILES_REF catalog (ca_bundle_path, ca_directory, client_cert_path/ client_key_path, minimum_version) — see agent-connector-sdk' transport_security. |
| `ARIS_TLS_PROFILE_REF` | — |  |
| `ARIS_OAUTH_URL` | — | 1. OAuth2 client-credentials (preferred for ARIS Cloud / Connect) |
| `ARIS_CLIENT_ID` | — |  |
| `ARIS_CLIENT_SECRET` | secret-injected |  |
| `ARIS_TENANT` | — |  |
| `ARIS_TOKEN` | secret-injected | 2. Static bearer token (alternative to OAuth) |
| `ARIS_USERNAME` | — | 3. HTTP basic auth (alternative) |
| `ARIS_PASSWORD` | secret-injected |  |
| `ARIS_PATHS_JSON` | — | Optional JSON overriding the default ARIS REST path templates per tenant e.g. {"models":"v2/repository/models","model_objects":"v2/models/{model_id}/objects"} |
| `ARIS_ENABLE_WRITE` | `False` | Allow (gated) attribute writes back onto ARIS models (KG writeback) |
| `TRANSPORT` | `stdio` | stdio, streamable-http, or sse |
| `HOST` | `0.0.0.0` |  |
| `PORT` | `8000` |  |
| `MCP_ENABLED_TOOLS` | — | Comma-separated tool / tag allow/deny lists |
| `MCP_DISABLED_TOOLS` | — |  |
| `MCP_ENABLED_TAGS` | — |  |
| `MCP_DISABLED_TAGS` | — |  |
| `DEBUG` | `False` |  |
| `PYTHONUNBUFFERED` | `1` |  |
| `ARISTOOL` | `True` | The action-routed ARIS tools (aris_model, aris_object) share this toggle. |
| `ENABLE_OTEL` | `True` |  |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — |  |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | — |  |
| `EUNOMIA_TYPE` | `none` |  |
| `EUNOMIA_POLICY_FILE` | `mcp_policies.json` |  |
| `EUNOMIA_REMOTE_URL` | — |  |

#### Inherited agent-connector-sdk variables (apply to every connector)

| Variable | Example | Description |
|----------|---------|-------------|
| `MCP_CLIENT_AUTH` | — | Outbound MCP child auth: `oidc-client-credentials` \| `basic` \| `none` |
| `OIDC_CLIENT_ID` | — | OIDC client id (service-account auth) |
| `OIDC_CLIENT_SECRET_REF` | `secret://identity/oidc-client-secret` | Runtime secret reference for the OIDC service account |
| `MCP_BASIC_AUTH_USERNAME` | — | HTTP Basic username (`MCP_CLIENT_AUTH=basic`) |
| `MCP_BASIC_AUTH_PASSWORD_REF` | `secret://identity/mcp-basic-password` | Runtime secret reference for HTTP Basic auth (`MCP_CLIENT_AUTH=basic`) |
| `MCP_URL` | `http://localhost:8000/mcp` | URL of the MCP server the agent connects to |
| `PROVIDER` | — | Operator-configured LLM provider for the agent |
| `MODEL_ID` | — | Operator-configured model id for the agent |
| `ENABLE_WEB_UI` | `True` | Serve the AG-UI web interface |

_28 package + 9 inherited variable(s). Auto-generated from `.env.example` + the shared agent-connector-sdk set — do not edit._
<!-- ENV-VARS-TABLE:END -->


Every variable the server reads, grouped by concern.

### Connection & Credentials
| Variable | Purpose | Default |
|----------|---------|---------|
| `ARIS_API_BASE` | ARIS REST base URL (tenant API root) | `http://localhost/abs/api` |
| `ARIS_TLS_PROFILE` / `ARIS_TLS_PROFILE_REF` | named outbound TLS policy from AgentConfig; verification is mandatory | _(empty, system trust)_ |
| `ARIS_OAUTH_URL` / `ARIS_CLIENT_ID` / `ARIS_CLIENT_SECRET` / `ARIS_TENANT` | OAuth2 client-credentials (preferred) | — |
| `ARIS_TOKEN` | static bearer token (alt to OAuth) | — |
| `ARIS_USERNAME` / `ARIS_PASSWORD` | HTTP basic (alt) | — |
| `ARIS_PATHS_JSON` | JSON overriding REST path templates per tenant | — |
| `ARIS_ENABLE_WRITE` | allow attribute writes | `False` |

> **Tenant differences.** ARIS deployments vary (Connect ABS portal vs the public
> ARIS API; on-prem vs Cloud). The defaults follow the common ARIS Connect ABS
> REST layout. If the operator's tenant's paths differ, set `ARIS_PATHS_JSON`, e.g.
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
> that pulls only the FastMCP / FastAPI tooling (`agent-connector-sdk`). It deliberately
> **excludes** the heavy agent runtime (the epistemic-graph engine, `pydantic-ai`,
> `dspy`, `llama-index`, `tree-sitter`), so `uvx`/container installs are dramatically
> Pydantic AI agent.

Pick the extra that matches what the operator want to run:

| Extra | Installs | Use when |
|-------|----------|----------|
| `aris-mcp[mcp]` | Slim MCP server only (`agent-connector-sdk` — FastMCP/FastAPI) | The operator only run the **MCP server** (smallest install / image) |
| `aris-mcp[all]` | Everything (`mcp` + `agent` + `logfire`) | Development / both surfaces |

```bash
# MCP server only (recommended for tool hosting — slim deps)
uv pip install "aris-mcp[mcp]"

# Everything (development)
uv pip install "aris-mcp[all]"      # or: python -m pip install "aris-mcp[all]"
```

### Container images (`:mcp`)

One multi-stage `docker/Dockerfile` builds the MCP-only image (`--target mcp`):

| Image tag | Build target | Contents | Entrypoint |
|-----------|--------------|----------|------------|
| `knucklessg1/aris-mcp:mcp` | `--target mcp` | `aris-mcp[mcp]` — **slim**, no engine/`pydantic-ai`/`dspy`/`llama-index`/`tree-sitter` | `aris-mcp` |

```bash
docker build --target mcp   -t knucklessg1/aris-mcp:mcp    docker/   # slim MCP server
```

agent (`:1.1.0`) with a co-located `:mcp` sidecar.

### Knowledge-graph database (`epistemic-graph`)

transitively via `agent-connector-sdk`). For production — or to share one knowledge graph
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

## MCP Configuration Examples

<!-- MCP-CONFIG-EXAMPLES:START -->

> **Install the connector-focused `[mcp]` extra.** Examples use `aris-mcp[mcp]` to add
> FastMCP / FastAPI through `agent-connector-sdk`; the required Agent Connector SDK core
> still carries `epistemic-graph[full]`. The `[agent-runtime]` extra additionally
> enables model orchestration.

#### stdio Transport (local IDEs — Cursor, Claude Desktop, VS Code)

```json
{
  "mcpServers": {
    "aris-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "aris-mcp[mcp]",
        "aris-mcp"
      ],
      "env": {
        "ARISTOOL": "True",
        "ARIS_API_BASE": "http://localhost/abs/api",
        "ARIS_ENABLE_WRITE": "False"
      }
    }
  }
}
```

Runtime references require an alias-aware launcher such as GraphOS. Other
launchers must omit those entries and inject the resolved values through their
own runtime secret boundary.

#### Streamable-HTTP Transport (networked / production)

```json
{
  "mcpServers": {
    "aris-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "aris-mcp[mcp]",
        "aris-mcp",
        "--transport",
        "streamable-http",
        "--port",
        "8000"
      ],
      "env": {
        "TRANSPORT": "streamable-http",
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "ARISTOOL": "True",
        "ARIS_API_BASE": "http://localhost/abs/api",
        "ARIS_ENABLE_WRITE": "False"
      }
    }
  }
}
```

Alternatively, connect to a pre-deployed Streamable-HTTP instance by `url`:

```json
{
  "mcpServers": {
    "aris-mcp": {
      "url": "http://localhost:8000/aris-mcp/mcp"
    }
  }
}
```

Run a reviewed container image as a least-privilege stdio child (no
listener or published port):

```bash
docker run -i --rm \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -e TRANSPORT=stdio \
  -e ARISTOOL=True \
  -e ARIS_API_BASE=http://localhost/abs/api \
  -e ARIS_ENABLE_WRITE=False \
  registry.example.invalid/aris-mcp@sha256:<digest> aris-mcp
```

For containerized network HTTP, supply an authenticated TLS ingress (or
direct server TLS), exact `MCP_ALLOWED_HOSTS`, and an exact trusted-proxy
CIDR policy through the operator-owned deployment profile. The generator
does not emit an unauthenticated non-loopback listener.

_Auto-generated from the code-read env surface (package vars) — do not edit._
<!-- MCP-CONFIG-EXAMPLES:END -->

## Deployment

1. **stdio** — `uv run aris-mcp` (see `mcp_config.json`).
2. **streamable-http** — `aris-mcp --transport streamable-http --port 8000`.
3. **local container** — build from `docker/` and run with the env above.
4. **remote** — point the operator's client at `https://aris-mcp.example.invalid/mcp`.


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
| Container, prod | deploy `knucklessg1/aris-mcp:1.1.0` via docker-compose / swarm / podman / podman-compose / kubernetes |
| Container, dev (editable) | deploy `docker/compose.dev.yml` (source-mounted at `/src`; edits live on restart) |

Secrets are read-existing + seeded via `vault_sync` — you are only prompted for what's missing.

<!-- END agent-os-genesis-deploy -->

<!-- GOVERNED-CAPABILITY:START -->
## Governed capability contract

This package ships a compact canonical skill surface with specialist procedures
kept as referenced workflows. The current MCP tools, skill metadata,
`connector_manifest.yml`, ontology, mappings, shapes, fixtures, migrations,
tool-schema fingerprints, and certification metadata form one versioned
capability contract. Validate them together; do not rely on stale tool names or
historical per-task skill wrappers.

Runtime endpoints, credentials, certificate trust, tenant identity, retention,
and observability policy are deployment inputs and are never packaged values.
See [Configuration, trust, and privacy](docs/configuration.md) before enabling a
network transport, connector ingestion, GraphOS delegation, or trace export.
<!-- GOVERNED-CAPABILITY:END -->


