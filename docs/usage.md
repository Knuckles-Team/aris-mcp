# Usage — API / CLI / MCP

`aris-mcp` exposes the same capability three ways: as **MCP tools** an agent calls,
as a **Python API** (`ArisApi`) the operator import, and as **command-line servers**. The
layered design is described in [Architecture](overview.md).

## As an MCP server

Once [deployed](deployment.md), the server registers one typed tool per operation.
With no `ARIS_API_BASE` and no `ARIS_REPOSITORY_DIR` the repository tools refuse
`ARIS_NOT_CONFIGURED` (a JSON tool error with `code`, `message`, `remedy`); the AML
and canonical conversion tools still work on AML text.

| Tool | Toggle | Surface |
|---|---|---|
| `aris_get_source_status` | `ARISTOOL` | Source mode (live, files, fixture, unconfigured), repository, model count, writes enabled |
| `aris_list_models` / `aris_get_model` | `ARISTOOL` | Model inventory and one model's record |
| `aris_list_model_objects` / `aris_list_model_connections` | `ARISTOOL` | A model's EPC objects (TypeNum, SymbolNum) and directed connections |
| `aris_get_model_attributes` | `ARISTOOL` | A model's attributes |
| `aris_set_model_attributes` / `aris_set_object_attributes` | `ARISTOOL` | Attribute writes (live tenant, `ARIS_ENABLE_WRITE=true`) |
| `aris_ingest_model_inventory` / `aris_ingest_model_graph` / `aris_ingest_model_export` | `ARISTOOL` | Knowledge-graph ingest |
| `aris_import_aml` / `aris_export_aml` | `ARISTOOL` | AML export reading and writing |
| `aris_export_canonical_workflow` / `aris_import_canonical_workflow` | `ARISTOOL` | EPC <-> canonical workflow (`medulla.process.canonical/v1`) |

Example agent prompts that map onto these tools:

- *"Which ARIS repository do you serve?"* → `aris_get_source_status`
- *"List the process models"* → `aris_list_models`
- *"Show the EPC functions and connections for model X"* → `aris_list_model_objects`, `aris_list_model_connections`
- *"Turn this AML export into the canonical workflow"* → `aris_export_canonical_workflow`
- *"Write the kg_intelligence attribute back onto model X"* → `aris_set_model_attributes`

## As a Python API

`ArisApi` is a granular `requests`-based facade covering model inventory, EPC
objects, connections, and attribute operations. Build one straight from the
environment with `get_client`, or build it directly.

```python
from aris_mcp.auth import get_client

api = get_client()        # reads ARIS_* from the environment / .env

# Reads
models = api.list_models()                       # model inventory
objects = api.get_model_objects(model_id="...")  # EPC functions / events / operators
conns = api.get_model_connections(model_id="...")# control-flow connections
attrs = api.get_model_attributes(model_id="...") # model attributes
```

Build the client directly:

```python
from aris_mcp.api_client import ArisApi

api = ArisApi(
    base_url="http://your-aris/abs/api",
    token="your-api-token",
)  # TLS is resolved through the shared AgentConfig transport profile
models = api.list_models()
```

### Writes

Attribute writeback is gated by `ARIS_ENABLE_WRITE`:

```python
api.set_model_attributes(model_id="...", attributes={"kg_intelligence": "..."})
```

## As a CLI

The package installs two console scripts.

Run the **MCP server** (stdio by default, or an HTTP transport):

```bash
aris-mcp
TRANSPORT=streamable-http HOST=0.0.0.0 PORT=8000 aris-mcp
```

Run the **Pydantic AI agent** against a running MCP server:

```bash
aris-agent --mcp-url http://localhost:8000
```

See [Deployment](deployment.md) for transports, environment configuration, and the
container recipes.
