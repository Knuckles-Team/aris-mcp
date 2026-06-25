# Installation

`aris-mcp` is a standard Python package and a prebuilt container image. Pick the
path that matches how you want to run it.

## Requirements

- **Python 3.11 – 3.14**.
- A reachable **Software AG ARIS** tenant (ARIS Connect / Enterprise / Cloud) — see
  [Backing Platform](platform.md) for connection details.

## From PyPI (recommended)

```bash
pip install aris-mcp
```

### Optional extras

The base install is intentionally minimal. Install the extra for what you need:

| Extra | Install | Pulls in |
|---|---|---|
| `mcp` | `pip install "aris-mcp[mcp]"` | FastMCP MCP-server runtime (`agent-utilities[mcp]`) |
| `agent` | `pip install "aris-mcp[agent]"` | Pydantic-AI agent + Logfire tracing |
| `all` | `pip install "aris-mcp[all]"` | Everything above |
| `test` | `pip install "aris-mcp[test]"` | `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-xdist` |

```bash
# Typical: run the MCP server and the agent
pip install "aris-mcp[all]"
```

## From source

```bash
git clone https://github.com/Knuckles-Team/aris-mcp.git
cd aris-mcp
pip install -e ".[all]"          # editable install with every extra
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv pip install -e ".[all]"
uv run aris-mcp
```

## Prebuilt Docker image

A multi-stage, slim image is published on every release (entrypoint `aris-mcp`):

```bash
docker pull knucklessg1/aris-mcp:mcp

docker run --rm -i \
  -e ARIS_API_BASE=http://your-aris/abs/api \
  -e ARIS_TOKEN=your-api-token \
  knucklessg1/aris-mcp:mcp        # stdio transport (default)
```

For an HTTP server with a published port, see [Deployment](deployment.md).

## Verify the install

```bash
aris-mcp --help
python -c "import aris_mcp; print(aris_mcp.__version__)"
```

## Next steps

- **[Deployment](deployment.md)** — run it as a long-lived MCP server behind Caddy + DNS.
- **[Usage](usage.md)** — call the tools, the API, and the agent.
- **[Configuration](deployment.md#configuration-environment)** — every environment variable.
