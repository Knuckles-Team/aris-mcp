---
name: aris-epc-to-canonical-workflow
skill_type: skill
description: >-
  Convert an ARIS EPC export into the canonical workflow
  (medulla.process.canonical/v1) that the engine builds the agent workflow
  graph from, and convert a canonical workflow (from BPMN or EPC) back to EPC
  and AML with its losses listed. Use when a business process authored in ARIS
  must run as an agent workflow, or a process from the process engine must be
  handed to ARIS. Do NOT use to read repository models (use
  aris-process-modeling) or ingest them (use aris-kg-ingestion).
license: MIT
tags: [aris, epc, bpmn, canonical-workflow, agent-dag, aml, mcp]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# EPC to canonical workflow and agent workflow graph input

Contracts: `convert-epc-to-canonical-workflow`, `convert-canonical-to-epc`
(`ontology://aris-mcp/contracts.ttl`). Data location: `canonical-workflow`.
Works in every source mode, including `unconfigured`, when the AML is passed in.

## 1. EPC export -> canonical workflow

1. `aris_import_aml(aml_text=<AML>)`: confirms the export reads and lists its
   models (`model.guid`, objects, connections). A DOCTYPE or entity declaration
   is refused `AML_INVALID`.
2. `aris_export_canonical_workflow(aml_text=<AML>, model_id=<guid>)` (or only
   `model_id` for a repository model). The result:
   - `steps`: `{id, kind, gate, label, role, ref}` with `id` `s1..sn` in the
     deterministic order. Kinds: `start`, `end`, `human` (function carried out
     by an organizational element, no application system; `role` = that
     element), `agent` (application-supported or unassigned function),
     `decision` (function linked to a business rule; `ref` = rule name),
     `call` (process interface), `branch`/`fork`/`join` (operators; `gate`
     `xor`/`or`/`and`, split or join by degree).
   - `flows`: `{source, target, condition, default}`; the event after an XOR or
     OR split becomes the condition.
   - `digest`: SHA-256 over schema, steps and flows only. Equal digests mean the
     same process, whichever format it was authored in.
   - `source.elements`: step id -> ARIS object guid; `annex`: intermediate
     events, condition-event ids and unknown attachments, kept for a
     same-source export; `losses`: empty for an EPC import.
3. Hand the whole JSON to the engine's process plan
   (`ProcessPlan` / process import). The engine builds the agent workflow graph
   from the canonical steps and flows only: nodes are the steps with their
   kinds, edges are the flows.

## 2. Canonical workflow -> EPC and AML

1. `aris_import_canonical_workflow(canonical=<JSON>, strict=true)`.
   `PROCESS_EXPORT_LOSSY` lists what EPC cannot express in `details`:
   `typed-trigger` (timer, message or signal waits), `boundary-event`,
   `default-flow`, `event-based-gateway`, `decision-table` (the table stays in
   the engine; only the rule reference is exported, for a canonical that did
   not come from ARIS), `unassigned-human-step`, and annex constructs of the
   other format.
2. Show the losses; only with the user's agreement call again with
   `strict=false`. The result has `model`, `objects`, `connections`, `aml` and
   `losses`. Nothing is written to the ARIS repository.

## 3. Prove a round trip

- Same source: EPC -> canonical -> EPC -> canonical keeps the digest and the
  annex (events and unknown attachments come back with their ids).
- Cross source: the BPMN and the EPC version of one process have the same
  digest. The worked example is the invoice-approval fixture (12 steps: start,
  human, decision, XOR branch, human, XOR join, agent, AND fork, two agents,
  AND join, end).
