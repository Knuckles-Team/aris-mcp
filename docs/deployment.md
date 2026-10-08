# Deployment

<!-- BEGIN GENERATED: deployment-options -->
## Deployment Options

`aris-mcp` supports local stdio, a loopback-only development listener, a
least-privilege stdio container, and a remote authenticated HTTPS boundary.
Provider endpoint, credential, selector, identity, and trust material are supplied
at runtime through `AgentConfig`; none is stored in this repository.

### Installed stdio process

```json
{
  "mcpServers": {
    "aris": {
      "command": "aris-mcp",
      "args": [],
      "env": {"MCP_TOOL_MODE": "intent"}
    }
  }
}
```

### Loopback development listener

```bash
aris-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Do not expose this listener beyond loopback. Network deployments require direct TLS
or an explicitly trusted TLS-terminating ingress, configured authentication, exact
`MCP_ALLOWED_HOSTS`, and an exact trusted-proxy CIDR policy.

### Least-privilege local container

```bash
docker run -i --rm \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -e TRANSPORT=stdio \
  registry.example.invalid/aris-mcp@sha256:<digest> aris-mcp
```

The operator projects the selected AgentConfig profile into the process at runtime;
the image remains immutable and contains no environment connection profile.

### Remote authenticated HTTPS endpoint

```json
{
  "mcpServers": {
    "aris": {"url": "https://service.example.invalid/mcp"}
  }
}
```

Store the real remote URL, outbound identity reference, and TLS-profile reference in
`AgentConfig`, not in MCP client JSON or documentation.
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
| `ARIS_TLS_PROFILE` / `ARIS_TLS_PROFILE_REF` | _(empty)_ | Named outbound TLS policy from AgentConfig (system trust by default); verification is mandatory and cannot be disabled |
| `ARIS_ENABLE_WRITE` | `False` | Allow gated attribute writeback |

OAuth2 client-credentials (`ARIS_OAUTH_URL` / `ARIS_CLIENT_ID` / `ARIS_CLIENT_SECRET`
/ `ARIS_TENANT`) and HTTP basic (`ARIS_USERNAME` / `ARIS_PASSWORD`) are alternatives
to a static token — see [Backing Platform](platform.md). Plus `HOST` / `PORT` /
`TRANSPORT` for HTTP transports. Copy
[`.env.example`](https://github.com/Knuckles-Team/aris-mcp/blob/main/.env.example)
to `.env` and populate the values the operator use; the server remains inactive when no
credentials are present.

## Docker Compose

The repo ships [`docker/mcp.compose.yml`](https://github.com/Knuckles-Team/aris-mcp/blob/main/docker/mcp.compose.yml).
It reads a sibling `.env` and publishes the HTTP server on `:8000`:

```yaml
services:
  aris-mcp:
    image: knucklessg1/aris-mcp:1.1.0
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
      - ARIS_TLS_PROFILE
      - ARIS_TLS_PROFILE_REF
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
    image: knucklessg1/aris-mcp:1.1.0
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

Expose the HTTP server on a hostname with automatic TLS. Add to the operator's `Caddyfile`:

```caddy
# Deployment-selected HTTPS hostname
aris-mcp.example.invalid {
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

Add to the operator's client's `mcp_config.json`:

```json
{
  "mcpServers": {
    "aris-mcp": {
      "command": "uv",
      "args": ["run", "aris-mcp"],
      "env": {
        "ARIS_API_BASE": "http://your-aris/abs/api",
        "ARIS_TOKEN": "your-api-token"
      }
    }
  }
}
```

For a remote HTTP server, point the client at `https://aris-mcp.example.invalid/mcp` instead.
