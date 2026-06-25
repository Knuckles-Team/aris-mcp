# Usage — API / CLI / MCP

`aris-mcp` exposes the same capability three ways: as **MCP tools** an agent calls,
as a **Python API** (`ArisApi`) you import, and as **command-line servers**. The
layered design is described in [Architecture](overview.md).

## As an MCP server

Once [deployed](deployment.md), the server registers two action-routed tools. Reads
work with no configuration beyond the connection details and valid credentials.

| Tool | Toggle | Surface |
|---|---|---|
| `aris_model` | `ARISTOOL` | List models, read per-model EPC objects (functions / events / rule operators) and control-flow connections, read model attributes |
| `aris_object` | `ARISTOOL` | Write attributes on a single ARIS object (gated by `ARIS_ENABLE_WRITE`) |

Example agent prompts that map onto these tools:

- *"List the process models in the tenant"* → `aris_model`
- *"Show the EPC functions and connections for model X"* → `aris_model`
- *"Write the kg_intelligence attribute back onto model X"* → `aris_object`

## As a Python API

`ArisApi` is a granular `requests`-based facade covering model inventory, EPC
objects, connections, and attribute operations. Build one straight from the
environment with `get_client`, or construct it directly.

```python
from aris_mcp.auth import get_client

api = get_client()        # reads ARIS_* from the environment / .env

# Reads
models = api.list_models()                       # model inventory
objects = api.get_model_objects(model_id="...")  # EPC functions / events / operators
conns = api.get_model_connections(model_id="...")# control-flow connections
attrs = api.get_model_attributes(model_id="...") # model attributes
```

Construct the client directly:

```python
from aris_mcp.api_client import ArisApi

api = ArisApi(
    base_url="http://your-aris/abs/api",
    token="your-api-token",
    verify=True,
)
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
