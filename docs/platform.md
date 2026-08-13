# Backing Platform — Software AG ARIS

`aris-mcp` is a **client** of a Software AG ARIS tenant (ARIS Connect / ARIS
Enterprise / ARIS Cloud). Unlike a self-hostable open-source service, ARIS is a
commercial platform, so this page covers how to **connect** to an existing tenant
rather than how to stand one up. For provisioning an ARIS environment, follow the
upstream [Software AG ARIS documentation](https://www.softwareag.com/en_corporate/platform/aris.html).

!!! note "Backing-system recipe"
    Each connector in the ecosystem follows the same convention — a
    `docs/platform.md` recipe for the system it integrates with. Systems offered
    only as a managed/commercial service (like ARIS) document the connection rather
    than a local Compose stack.

## Connection model

ARIS deployments vary (Connect ABS portal vs the public ARIS API; on-prem vs Cloud),
so the REST base URL and path layout differ per tenant. The defaults follow the
common ARIS Connect ABS REST layout.

| Variable | Purpose | Default |
|---|---|---|
| `ARIS_API_BASE` | ARIS REST base URL (tenant API root) | `http://localhost/abs/api` |
| `ARIS_SSL_VERIFY` | Verify TLS (required; configure a trusted CA bundle for private PKI) | `True` |
| `ARIS_PATHS_JSON` | JSON overriding REST path templates per tenant | — |

If your tenant's paths differ from the ABS defaults, set `ARIS_PATHS_JSON`, e.g.:

```json
{"models":"v2/repository/models","model_objects":"v2/models/{model_id}/objects"}
```

## Authentication

The client tries credentials in order (first match wins):

1. **OAuth2 client-credentials** (preferred for ARIS Cloud / Connect) —
   `ARIS_OAUTH_URL` + `ARIS_CLIENT_ID` + `ARIS_CLIENT_SECRET` (+ optional
   `ARIS_TENANT`).
2. **Static bearer token** — `ARIS_TOKEN`.
3. **HTTP basic** — `ARIS_USERNAME` / `ARIS_PASSWORD`.

## Connect aris-mcp

Point the connector at your tenant and provide credentials:

```bash
export ARIS_API_BASE=https://aris.example.invalid/abs/api
export ARIS_TOKEN=your-api-token
export ARIS_SSL_VERIFY=True
export SSL_CERT_FILE=/run/secrets/enterprise-ca.pem

aris-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

Or with the OAuth2 client-credentials flow:

```bash
export ARIS_API_BASE=https://your-tenant.ariscloud.com/api
export ARIS_OAUTH_URL=https://your-tenant.ariscloud.com/oauth/token
export ARIS_CLIENT_ID=your-client-id
export ARIS_CLIENT_SECRET=your-client-secret
export ARIS_TENANT=your-tenant

aris-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

With the connection live, the [Python API](usage.md#as-a-python-api) and the
[MCP tools](usage.md#as-an-mcp-server) read model inventory, EPC structure, and
attributes — and (when `ARIS_ENABLE_WRITE=True`) write attributes back onto ARIS
models for Knowledge-Graph enrichment.
