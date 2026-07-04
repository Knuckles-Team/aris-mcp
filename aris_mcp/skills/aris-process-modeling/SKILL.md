---
name: aris-process-modeling
description: >-
  Read Software AG ARIS process models over the aris-mcp MCP server — list the
  model inventory, fetch one model's metadata/attributes, and read its EPC
  objects (functions/events/rule operators) and directed control-flow
  connections. Use when the agent must inventory ARIS models, open one model by
  GUID, or inspect a model's EPC structure. Do NOT use for ingesting models into
  the knowledge graph (use aris-kg-ingestion) or for control-flow / bottleneck
  analysis of a whole repository (use aris-process-mining).
license: MIT
tags: [aris, bpm, epc, process-model, rest-api, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# ARIS Process Modeling

Domain-typed, read-first access to Software AG **ARIS** process/architecture models
(EPC — Event-driven Process Chains) over the ARIS Connect / ARIS Enterprise / ARIS
Cloud REST API. Prefer these tools over raw HTTP — they carry the ARIS path templates
and return model-shaped records.

## When to use
- List the model inventory in a tenant/database (process + architecture models).
- Fetch a single model's metadata + attributes by GUID.
- Read a model's EPC objects (functions, events, rule operators).
- Read the directed control-flow connections between a model's objects.

## When NOT to use
- Pushing models into the knowledge graph → `aris-kg-ingestion`.
- Whole-repository control-flow / bottleneck / conformance analysis →
  `aris-process-mining`.
- Any attribute **write** unless `ARIS_ENABLE_WRITE=True` and you were explicitly
  asked to enrich a model (that is gated writeback, not modeling).

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`aris-mcp`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `ARIS_API_BASE` | ✅ | REST base URL (default `http://localhost/abs/api`) |
| `ARIS_OAUTH_URL` + `ARIS_CLIENT_ID` + `ARIS_CLIENT_SECRET` | one auth path | OAuth2 client-credentials (+ optional `ARIS_TENANT`) |
| `ARIS_TOKEN` | one auth path | static bearer token |
| `ARIS_USERNAME` / `ARIS_PASSWORD` | one auth path | HTTP basic |
| `ARIS_SSL_VERIFY` | optional | TLS verification toggle |
| `ARIS_PATHS_JSON` | optional | JSON overriding the default REST path templates per tenant |

`MCP_TOOL_MODE` (`condensed`|`verbose`|`both`) selects the condensed surface (below)
vs. the one-to-one verbose tools.

## Tools & actions
Prefer the **condensed** tool; it takes `action` + a `params_json` **JSON string**.

| Condensed tool | Actions |
|----------------|---------|
| `aris_model` | `list`, `get`, `objects`, `connections`, `attributes` |

### Key parameters
- `model_id` — the ARIS model **GUID**; required for `get` / `objects` / `connections`
  / `attributes`.
- `list` takes optional tenant-specific filter fields in `params_json`.

## Recipes (`params_json`)
List the model inventory:
```json
{}
```
Get one model's metadata:
```json
{"model_id": "<model-guid>"}
```
Read a model's EPC objects (functions/events/rules):
```json
{"model_id": "<model-guid>"}
```
Read a model's control-flow connections:
```json
{"model_id": "<model-guid>"}
```

## Gotchas
- `params_json` is a **string** of JSON, not an object — serialize it.
- ARIS deployments differ (Connect ABS portal vs. the public ARIS API; on-prem vs.
  Cloud). If reads 404, the REST path layout differs — set `ARIS_PATHS_JSON` to match
  your tenant (keys: `models`, `model`, `model_objects`, `model_connections`,
  `model_attributes`, `object_attributes`).
- Records key the model/object identifier under varying spellings (`guid`, `id`,
  `modelGuid`); read the GUID off whichever the tenant returns.
- EPC object `type`/`symbol` classifies the node: `*event*` → event,
  `*rule*/*operator*/AND/OR/XOR` → rule operator, otherwise a function.

## Related
- `aris-process-mining` — control-flow / bottleneck analysis built on these reads.
- `aris-kg-ingestion` — push these models into the knowledge graph as typed nodes.
