---
name: aris-process-mining
skill_type: skill
description: >-
  Analyze the control flow of Software AG ARIS EPC models over the aris-mcp MCP
  server — trace event→function→event paths, find splits/joins at rule
  operators, spot disconnected or dead-end objects, and reason about a model's
  structure. Use when the agent must explain how a process flows, validate an
  EPC's connectedness, or compare paths through a model. Do NOT use to merely
  list/read models (use aris-process-modeling) or to ingest them into the
  knowledge graph (use aris-kg-ingestion).
license: MIT
tags: [aris, process-mining, epc, control-flow, analysis, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# ARIS Process Mining

Control-flow reasoning over ARIS **EPC** models: given a model's objects and
connections, trace how work moves from a start event through functions and rule
operators to an end event, and surface structural problems. Reads come from the
`aris_model` tool (see `aris-process-modeling`); this skill is the analysis layer.

## When to use
- Explain how a process flows: start event → function → intermediate events → end.
- Identify splits/joins and their logic (AND / OR / XOR rule operators).
- Find structural issues: disconnected objects, dead ends, functions with no
  triggering event, events with no consuming function.
- Compare alternative paths through a model.

## When NOT to use
- Just listing or fetching a model's raw records → `aris-process-modeling`.
- Persisting the model + its flow into the KG → `aris-kg-ingestion`.
- Cross-repository process portfolios beyond a single model's graph — pull each
  model then aggregate (there is no single portfolio tool).

## Prerequisites & environment
Same connection as `aris-process-modeling` (the `aris-mcp` server + `ARIS_API_BASE`
and one auth path). See that skill's env matrix. This skill adds no new variables.

## Tools & actions
| Condensed tool | Actions used |
|----------------|--------------|
| `aris_model` | `objects`, `connections`, `get` |

Build the flow graph yourself from two reads:
- `aris_model` action=`objects` → the EPC nodes (classify each: function / event /
  rule operator).
- `aris_model` action=`connections` → the directed edges (`sourceObjectId` →
  `targetObjectId`, with a connection `type`).

## Recipes
Fetch the two halves of the flow graph for one model:
```json
{"model_id": "<model-guid>"}
```
(call once with action=`objects`, once with action=`connections`).

Then reason locally:
- adjacency = map each object GUID → outgoing target GUIDs from the connections.
- start events = events with no incoming edge; end events = events with no outgoing.
- a well-formed EPC alternates event → function → event; a function fanning to
  multiple functions/events without an intervening rule operator is a smell.
- unreachable objects = GUIDs never appearing as a connection target (except starts).

## Gotchas
- ARIS edges are directed; `sourceObjectId`/`targetObjectId` may also appear as
  `source`/`target` or `sourceGuid`/`targetGuid` depending on the tenant — read
  whichever is present.
- Rule operators (AND/OR/XOR) are first-class objects, not edge attributes — the flow
  passes *through* them; don't collapse them or you lose the branch logic.
- A large model can return many objects/connections; page or filter at the modeling
  layer before analysis if the tenant supports it.
- Connectors are control-flow only here — resource/data/org assignments are separate
  ARIS relationship types not covered by `connections`.

## Related
- `aris-process-modeling` — the reads this analysis consumes.
- `aris-kg-ingestion` — persist the analyzed flow as `:flowsTo` edges in the KG for
  cross-model querying.
