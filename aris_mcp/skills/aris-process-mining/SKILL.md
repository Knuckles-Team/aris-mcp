---
name: aris-process-mining
skill_type: skill
description: >-
  Analyse the control flow of ARIS EPC models over the aris-mcp MCP server:
  trace event -> function -> event paths, find splits and joins at rule
  operators, spot disconnected or dead-end objects and non-alternating chains,
  and compare paths. Use when the agent must explain how a process flows or
  validate an EPC's structure. Do NOT use to merely read models (use
  aris-process-modeling), to ingest them (use aris-kg-ingestion) or to convert
  them (use aris-epc-to-canonical-workflow).
license: MIT
tags: [aris, process-mining, epc, control-flow, analysis, mcp]
metadata:
  author: Knuckles-Team
  version: '2.0.0'
---
# ARIS process mining

Contract: `read-process-model` (`ontology://aris-mcp/contracts.ttl`).

## Build the flow graph

1. `aris_list_model_objects(model_id=<guid>)`: nodes. Control objects are
   `OT_FUNC` (functions; `ST_PRCS_IF` is a process interface), `OT_EVT`
   (events) and `OT_RULE` (operators: `ST_OPR_AND_1`, `ST_OPR_OR_1`,
   `ST_OPR_XOR_1`). Everything else is attached to a function.
2. `aris_list_model_connections(model_id=<guid>)`: edges
   `sourceObjectId -> targetObjectId`. Keep the edges whose two ends are
   control objects; the rest are attachments (`CT_EXEC_1` performer,
   `CT_CAN_SUPP_1` application support, business rule links).

## What to check

- Start events have no incoming edge, end events no outgoing edge.
- Strict EPC alternates event and function; a function directly followed by a
  function is a modelling gap.
- After an XOR or OR split each path starts with an event naming its condition.
- An object never reached from a start event, or a path that never reaches an
  end event, is a defect.
- Each split operator has a matching join of the same operator.

For the same analysis on the canonical form, call
`aris_export_canonical_workflow(model_id=<guid>)`: the steps are already typed
(`human`, `agent`, `decision`, `branch`, `fork`, `join`, ...) and intermediate
events are folded into flow conditions and the annex.

## Related
- `aris-process-modeling`: the reads this analysis consumes.
- `aris-epc-to-canonical-workflow`: the canonical form of the same model.
