# aris-mcp

Software AG **ARIS** REST API + **MCP Server and Agent** for the agent-utilities
ecosystem — process / enterprise-architecture (EPC) model inventory, per-model
objects and connections, and attribute read/write exposed as typed, deterministic
tools an agent can call.

!!! info "Official documentation"
    This site is the canonical reference for `aris-mcp`, maintained alongside
    every release.

[![PyPI](https://img.shields.io/pypi/v/aris-mcp)](https://pypi.org/project/aris-mcp/)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
[![License](https://img.shields.io/pypi/l/aris-mcp)](https://github.com/Knuckles-Team/aris-mcp/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/source-GitHub-181717?logo=github)](https://github.com/Knuckles-Team/aris-mcp)

## Overview

`aris-mcp` wraps the [Software AG ARIS](https://www.softwareag.com/en_corporate/platform/aris.html)
REST API with typed, deterministic MCP tools and a Pydantic AI agent. It provides:

- **`ArisApi`** — a granular `requests`-based REST facade covering model inventory,
  per-model EPC objects (functions / events / rule operators), control-flow
  connections, and attribute read/write surfaces of the ARIS API.
- **A FastMCP tool surface** registering the action-routed `aris_model` and
  `aris_object` tools (model inventory, EPC structure, attribute read, and gated
  attribute write).
- **A Pydantic AI agent** (`aris-agent`) that drives the MCP tools for autonomous
  ARIS process-model exploration and Knowledge-Graph enrichment.

The server remains inactive when credentials are absent and connects to any ARIS
tenant (ARIS Connect / ARIS Enterprise / ARIS Cloud) over its REST API.

## Explore the documentation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Installation](installation.md)** — pip, source, extras, and the prebuilt Docker image.
- :material-server-network: **[Deployment](deployment.md)** — run the MCP and agent servers, Docker Compose, Caddy + ARIS.
- :material-console: **[Usage](usage.md)** — the MCP tools, the `ArisApi` client, and the CLI.
- :material-database-cog: **[Backing Platform](platform.md)** — connect to an ARIS tenant.
- :material-sitemap: **[Architecture](overview.md)** — the layered API / MCP / agent design.
- :material-tag-multiple: **[Concepts](concepts.md)** — the `CONCEPT:ARIS-*` registry.

</div>

## Quick start

```bash
pip install "aris-mcp[mcp]"
aris-mcp                       # stdio MCP server (default transport)
```

Connect it to an ARIS tenant:

```bash
export ARIS_API_BASE=http://your-aris/abs/api
export ARIS_TOKEN=your-api-token
aris-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

See **[Installation](installation.md)** and **[Deployment](deployment.md)** for the
full matrix (PyPI extras, Docker image, all transports, reverse proxy, DNS).
