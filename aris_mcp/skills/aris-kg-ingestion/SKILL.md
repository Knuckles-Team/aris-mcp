---
name: aris-kg-ingestion
skill_type: skill
description: >-
  Natively ingest Software AG ARIS process models into the epistemic-graph
  knowledge graph over the aris-mcp MCP server — push models as typed
  :ProcessModel nodes, a single model's EPC objects as :EPCFunction/:EPCEvent/
  :EPCRule with :flowsTo control-flow edges, and raw model exports as
  content-addressed :ModelExport (:MediaAsset) blobs. Use when the agent must
  mirror ARIS content into the KG for cross-source querying. Do NOT use to merely
  read models (use aris-process-modeling) or to analyze a single model's flow in
  place (use aris-process-mining).
license: MIT
tags: [aris, knowledge-graph, ingestion, epc, blob, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# ARIS Knowledge-Graph Ingestion

The native "maximum ingestion" seam for ARIS: push process models into the ONE
epistemic-graph engine as typed OWL nodes + control-flow links, and store raw model
exports as durable blobs. Backed by `aris_mcp/kg_ingest.py` (typed nodes) and
`aris_mcp/kg_media.py` (blobs), federated by the `aris.ttl` ontology.
CONCEPT:AU-KG.ingest.enterprise-source-extractor

## When to use
- Mirror the ARIS model inventory into the KG as `:ProcessModel` nodes.
- Ingest ONE model's full EPC graph: objects as `:EPCFunction`/`:EPCEvent`/`:EPCRule`,
  control flow as `:flowsTo` (+ reified `:ProcessConnection`) edges.
- Store a raw model export (BPMN/XML/AML/SVG/PDF bytes) as a `:ModelExport`
  (`:MediaAsset`) content-addressed blob linked to its model.

## When NOT to use
- Only reading/inspecting a model → `aris-process-modeling`.
- Analyzing a single model's flow without persisting it → `aris-process-mining`.
- Writing enrichment attributes back **into** ARIS → that is the gated
  `aris_model`/`aris_object` `set_attributes` writeback, not KG ingestion.

## Prerequisites & environment
Same `aris-mcp` connection as `aris-process-modeling`. Ingestion is **best-effort and
engine-guarded**: with no reachable epistemic-graph engine, every ingest tool cleanly
no-ops (`"ingested": null`) and the connector keeps working. No KG infrastructure is
required for the read tools to function.

## Tools & actions
| Tool | Purpose |
|------|---------|
| `aris_ingest_models` | ingest the inventory (`:ProcessModel`) or one model's full EPC graph |
| `aris_ingest_model_export` | store a raw model export blob (`:ModelExport`) |

### Node id scheme (stable, dedupe-friendly)
- model → `aris:model:<guid>` (`:ProcessModel`)
- object → `aris:object:<guid>` (`:EPCFunction` / `:EPCEvent` / `:EPCRule`)
- connection → `aris:connection:<guid>` (`:ProcessConnection`)

## Recipes (`params_json`)
Ingest the whole model inventory as `:ProcessModel` nodes:
```json
{}
```
Ingest ONE model with its objects + control-flow edges:
```json
{"model_id": "<model-guid>"}
```
Store a raw model export blob (bytes base64-encoded):
```json
{"model_id": "<model-guid>", "model_name": "Order-to-Cash", "mime_type": "application/xml", "export_format": "bpmn", "data_b64": "<base64-bytes>"}
```

## Gotchas
- `aris_ingest_model_export` takes the export **bytes base64-encoded** in `data_b64`
  (the model is rendered/exported out-of-band; this tool only durably stores it).
- EPC subclassing is inferred from the object's ARIS `type`/`symbol`: `*event*` →
  `:EPCEvent`, `*rule*/*operator*/AND/OR/XOR` → `:EPCRule`, else `:EPCFunction`.
- Ingestion is idempotent by node id (MERGE on `aris:model:<guid>` etc.) — re-running
  updates rather than duplicates.
- `"ingested": null` is not an error — it means no engine was reachable; the `listed`
  count still reflects what was read from ARIS.

## Related
- `aris-process-modeling` — the reads feeding ingestion.
- `aris-process-mining` — analyze flow before/after persisting it.
- The agent-utilities `agent-utilities-source-integration` skill covers the hub-side
  `source_sync` path that consumes the `aris-models` connector preset.
