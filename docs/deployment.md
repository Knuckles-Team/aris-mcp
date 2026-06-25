# Deployment

<!-- BEGIN GENERATED: deployment-options -->
## Deployment Options

`aris-mcp` exposes its MCP server (console script `aris-mcp`) four ways. Pick the row that
matches where the server runs relative to your MCP client, then copy the matching
`mcp_config.json` below. Replace the `<your-…>` placeholders with the values from the **Configuration / Environment Variables** section.

| # | Option | Transport | Where it runs | `mcp_config.json` key |
|---|--------|-----------|---------------|------------------------|
| 1 | stdio | `stdio` | client launches a subprocess | `command` |
| 2 | Streamable-HTTP (local) | `streamable-http` | a local network port | `command` or `url` |
| 3 | Local container / uv | `stdio` or `streamable-http` | Docker / Podman / uv on this host | `command` or `url` |
| 4 | Remote URL | `streamable-http` | a remote host behind Caddy | `url` |

### 1. stdio (local subprocess)

The client launches the server over stdio via `uvx` — best for local IDEs
(Cursor, Claude Desktop, VS Code):

```json
{
  "mcpServers": {
    "aris-mcp": {
      "command": "uvx",
      "args": ["--from", "aris-mcp", "aris-mcp"],
      "env": {
        "ARIS_API_BASE": "<your-aris_api_base>",
        "ARIS_TOKEN": "<your-aris_token>"
      }
    }
  }
}
```

### 2. Streamable-HTTP (local process)

Run the server as a long-lived HTTP process:

```bash
uvx --from aris-mcp aris-mcp --transport streamable-http --host 0.0.0.0 --port 8000
curl -s http://localhost:8000/health        # {"status":"OK"}
```

Then either let the client launch it:

```json
{
  "mcpServers": {
    "aris-mcp": {
      "command": "uvx",
      "args": ["--from", "aris-mcp", "aris-mcp", "--transport", "streamable-http", "--port", "8000"],
      "env": {
        "TRANSPORT": "streamable-http",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "ARIS_API_BASE": "<your-aris_api_base>",
        "ARIS_TOKEN": "<your-aris_token>"
      }
    }
  }
}
```

…or connect to the already-running process by URL:

```json
{
  "mcpServers": {
    "aris-mcp": { "url": "http://localhost:8000/mcp" }
  }
}
```

### 3. Local container / uv

**(a) Launch a container directly from `mcp_config.json`** (stdio over the container —
no ports to manage). Swap `docker` for `podman` for a daemonless runtime:

```json
{
  "mcpServers": {
    "aris-mcp": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TRANSPORT=stdio",
        "-e", "ARIS_API_BASE=<your-aris_api_base>",
        "-e", "ARIS_TOKEN=<your-aris_token>",
        "knucklessg1/aris-mcp:mcp"
      ]
    }
  }
}
```

**(b) Run a local streamable-http container, then connect by URL:**

```bash
docker run -d --name aris-mcp -p 8000:8000 \
  -e TRANSPORT=streamable-http \
  -e PORT=8000 \
  -e ARIS_API_BASE="<your-aris_api_base>" \
  -e ARIS_TOKEN="<your-aris_token>" \
  knucklessg1/aris-mcp:mcp
# or, from a clone of this repo:
docker compose -f docker/mcp.compose.yml up -d
```

```json
{
  "mcpServers": {
    "aris-mcp": { "url": "http://localhost:8000/mcp" }
  }
}
```

**(c) From a local checkout with `uv`:**

```bash
uv run aris-mcp --transport streamable-http --port 8000
```

### 4. Remote URL (deployed behind Caddy)

When the server is deployed remotely (e.g. as a Docker service) and published through
Caddy on the internal `*.arpa` zone, connect with the `"url"` key — no local process or
image required:

```json
{
  "mcpServers": {
    "aris-mcp": { "url": "http://aris-mcp.arpa/mcp" }
  }
}
```

Caddy reverse-proxies `http://aris-mcp.arpa` to the container's `:8000`
streamable-http listener; `http://aris-mcp.arpa/health` returns
`{"status":"OK"}` when the service is live.
<!-- END GENERATED: deployment-options -->

This page covers running `aris-mcp` as a long-lived server: the transports,
a Docker Compose stack, putting it behind a Caddy reverse proxy, and giving it a DNS
name. To connect it to an **ARIS tenant**, see [Backing Platform](platform.md).

> `aris-mcp` ships **two** console scripts: an **MCP server** (`aris-mcp`) and a
> **Pydantic AI agent** (`aris-agent`). The MCP server is a typed, deterministic tool
> surface; the agent connects to it and drives the tools autonomously.

## Run the MCP server

The transport is selected with `--transport` (or the `TRANSPORT` env var):

=== "stdio (default)"

    ```bash
    aris-mcp
    ```
    For IDE / desktop MCP clients that launch the server as a subprocess.

=== "streamable-http"

    ```bash
    aris-mcp --transport streamable-http --host 0.0.0.0 --port 8000
    ```
    A network server with a `/health` endpoint and `/mcp` route.

=== "sse"

    ```bash
    aris-mcp --transport sse --host 0.0.0.0 --port 8000
    ```

Health check (HTTP transports):

```bash
curl -s http://localhost:8000/health        # {"status":"OK"}
```

## Configuration (environment)

`aris-mcp` is configured entirely from the environment. The core connection set:

| Var | Default | Meaning |
|---|---|---|
| `ARIS_API_BASE` | `http://localhost/abs/api` | ARIS REST base URL (tenant API root) |
| `ARIS_TOKEN` | _(empty)_ | Static bearer token (alt to OAuth / basic) |
| `ARIS_SSL_VERIFY` | `True` | Verify TLS (set `False` for self-signed homelab) |
| `ARIS_ENABLE_WRITE` | `False` | Allow gated attribute writeback |

OAuth2 client-credentials (`ARIS_OAUTH_URL` / `ARIS_CLIENT_ID` / `ARIS_CLIENT_SECRET`
/ `ARIS_TENANT`) and HTTP basic (`ARIS_USERNAME` / `ARIS_PASSWORD`) are alternatives
to a static token — see [Backing Platform](platform.md). Plus `HOST` / `PORT` /
`TRANSPORT` for HTTP transports. Copy
[`.env.example`](https://github.com/Knuckles-Team/aris-mcp/blob/main/.env.example)
to `.env` and populate the values you use; the server remains inactive when no
credentials are present.

## Docker Compose

The repo ships [`docker/mcp.compose.yml`](https://github.com/Knuckles-Team/aris-mcp/blob/main/docker/mcp.compose.yml).
It reads a sibling `.env` and publishes the HTTP server on `:8000`:

```yaml
services:
  aris-mcp:
    image: knucklessg1/aris-mcp:latest
    container_name: aris-mcp
    hostname: aris-mcp
    restart: always
    env_file:
      - ../.env
    environment:
      - PYTHONUNBUFFERED=1
      - HOST=0.0.0.0
      - PORT=8000
      - TRANSPORT=streamable-http
      - ARIS_API_BASE
      - ARIS_TOKEN
      - ARIS_SSL_VERIFY
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
cp .env.example .env          # then edit ARIS_* values
docker compose -f docker/mcp.compose.yml up -d
docker compose -f docker/mcp.compose.yml logs -f
```

## Agent server

The Pydantic AI agent (`aris-agent`) connects to a running MCP server and drives its
tools. Point it at the MCP server with `--mcp-url`:

```bash
aris-agent --mcp-url http://localhost:8000 --host 0.0.0.0 --port 8080
```

A container recipe mirrors the MCP service, wiring `MCP_URL` to the MCP server by
container name and publishing the agent on `:8080`:

```yaml
# docker/agent.compose.yml
services:
  aris-agent:
    image: knucklessg1/aris-mcp:latest
    container_name: aris-agent
    hostname: aris-agent
    restart: always
    entrypoint: ["aris-agent"]
    depends_on: [aris-mcp]
    env_file:
      - ../.env
    environment:
      - PYTHONUNBUFFERED=1
      - MCP_URL=http://aris-mcp:8000
      - HOST=0.0.0.0
      - PORT=8080
    ports:
      - "8080:8080"
```

## Behind a Caddy reverse proxy

Expose the HTTP server on a hostname with automatic TLS. Add to your `Caddyfile`:

```caddy
# Internal (self-signed) — homelab .arpa zone
aris-mcp.arpa {
    tls internal
    reverse_proxy aris-mcp:8000
}
```

```caddy
# Public — automatic Let's Encrypt
aris-mcp.example.com {
    reverse_proxy aris-mcp:8000
}
```

Reload Caddy:

```bash
docker compose -f services/caddy/compose.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Register with an MCP client

Add to your client's `mcp_config.json`:

```json
{
  "mcpServers": {
    "aris-mcp": {
      "command": "uv",
      "args": ["run", "aris-mcp"],
      "env": {
        "ARIS_API_BASE": "http://your-aris/abs/api",
        "ARIS_TOKEN": "your-api-token",
        "ARIS_SSL_VERIFY": "True"
      }
    }
  }
}
```

For a remote HTTP server, point the client at `http://aris-mcp.arpa/mcp` instead.
