---
name: aris-kg-ingestion
skill_type: skill
description: >-
  Ingest ARIS process models into the knowledge graph over the aris-mcp MCP
  server: the model inventory as model nodes, one model's objects typed by
  their leaf EPC class (:EpcHumanFunction, :EpcAutomatedFunction,
  :EpcDecisionFunction, :EpcProcessInterface, :EpcStartEvent, :EpcEndEvent,
  :EpcIntermediateEvent, :EpcAndOperator/:EpcOrOperator/:EpcXorOperator,
  attachments) with reified :EpcConnection nodes and :flowsTo edges, and raw
  exports as content-addressed :ModelExport blobs. Use when the agent must
  mirror ARIS content into the graph. Do NOT use to merely read models (use
  aris-process-modeling).
license: MIT
tags: [aris, knowledge-graph, ingestion, epc, blob, mcp]
metadata:
  author: Knuckles-Team
  version: '2.0.0'
---
# ARIS knowledge-graph ingestion

Contract: `ingest-process-models` (`ontology://aris-mcp/contracts.ttl`).
CONCEPT:AU-KG.ingest.enterprise-source-extractor

## Tools

| Tool | Writes |
|---|---|
| `aris_ingest_model_inventory(name=...)` | one model node per model (`:EpcModel` for EPC types) |
| `aris_ingest_model_graph(model_id=<guid>)` | the model, each object as its leaf class with `:hasObject`, each connection as `:EpcConnection` (`:hasConnection`, `:connectionSource`, `:connectionTarget`) plus `:flowsTo` |
| `aris_ingest_model_export(model_id, data_b64, mime_type, export_format)` | the export bytes as a `:ModelExport` blob |
| `aris_import_aml(aml_text=..., ingest=true)` | every model of an AML export, without a repository |

Objects are typed by their ARIS TypeNum and SymbolNum through the ontology
annotations; type-name hints are used only when a tenant returns names instead
of constants. A function's leaf class depends on its attachments: a performer
and no application system is human, a business rule makes it a decision.

## Node ids

`aris:model:<guid>`, `aris:object:<guid>`, `aris:connection:<guid>` (a
connection without its own guid gets one from its model, ends and type).
Ingest is idempotent by id.

## Gotchas
- `"ingested": null` means no engine was reachable; the counts still show what
  was read.
- In `unconfigured` mode the repository tools refuse `ARIS_NOT_CONFIGURED`; use
  `aris_import_aml` with an export instead.
- Fixture-repository models are samples; do not ingest them as business data.
