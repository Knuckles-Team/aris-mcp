---
name: aris-process-modeling
skill_type: skill
description: >-
  Read ARIS EPC process models over the aris-mcp MCP server: check which
  repository the connector serves (live tenant, AML directory, bundled fixture
  or unconfigured), list the model inventory, fetch one model, its attributes,
  its objects (functions, events, rule operators, attached objects) and its
  connections, and export a model as AML. Use when the agent must inventory ARIS
  models or inspect one model's EPC structure. Do NOT use for knowledge-graph
  ingest (use aris-kg-ingestion), control-flow analysis (use
  aris-process-mining) or conversion to the canonical workflow (use
  aris-epc-to-canonical-workflow).
license: MIT
tags: [aris, bpm, epc, process-model, aml, mcp]
metadata:
  author: Knuckles-Team
  version: '2.0.0'
---
# ARIS process modeling

Contracts: `verify-process-source`, `read-process-model`, `export-model-aml`,
`enrich-model-attributes` (`ontology://aris-mcp/contracts.ttl`). Data locations:
`process-repository`, `process-model-graph`, `model-exports`.

## 1. Know the source first

`aris_get_source_status()` returns `mode`, `repository`, `model_count` and
`writes_enabled`.

| mode | set by | behaviour |
|---|---|---|
| `live` | `ARIS_API_BASE` (+ OAuth, token or basic auth) | the ARIS REST tenant |
| `files` | `ARIS_REPOSITORY_DIR=<dir of .aml exports>` | read-only, served from the exports |
| `fixture` | `ARIS_REPOSITORY_DIR=fixture` | the bundled sample repository; responses say `"repository": "fixture"`; never business data |
| `unconfigured` | nothing set | every repository tool refuses `ARIS_NOT_CONFIGURED` |

A refusal is an error result (`isError`) whose structured content is
`{"refused": true, "code", "message", "remedy"}`.
Act on the remedy.

## 2. Read

1. `aris_list_models(name=..., limit=..., offset=...)`: `items` of
   `{guid, id, name, type, groupPath, attributes}`; EPC models have type `MT_EEPC`.
2. `aris_get_model(model_id=<guid>)`: one model record.
3. `aris_list_model_objects(model_id=<guid>)`: `{guid, id, name, type, symbol}`.
   `type` is the ARIS TypeNum (`OT_FUNC`, `OT_EVT`, `OT_RULE`, `OT_ORG_UNIT`,
   `OT_APPL_SYS_TYPE`, `OT_BUSINESS_RULE`, ...); `symbol` the SymbolNum
   (`ST_PRCS_IF` is a process interface, `ST_OPR_XOR_1`/`ST_OPR_OR_1`/
   `ST_OPR_AND_1` the operators).
4. `aris_list_model_connections(model_id=<guid>)`:
   `{guid, type, sourceObjectId, targetObjectId}`. Control flow joins two
   control objects; any other connection attaches an object to a function
   (`CT_EXEC_1` = carried out by).
5. `aris_get_model_attributes(model_id=<guid>)`.
6. `aris_export_aml(model_id=<guid>)`: the model as AML text.

The ontology `ontology://aris-mcp/aris.ttl` names the class of every TypeNum and
SymbolNum and the canonical step kind it becomes.

## 3. Write (live tenant only, with approval)

`aris_set_model_attributes(model_id, attributes={"AT_DESC": "..."})` and
`aris_set_object_attributes(object_id, attributes={...})` write only to a live
tenant with `ARIS_ENABLE_WRITE=true`. Otherwise they refuse
`ARIS_WRITE_DISABLED` (live) or `ARIS_READ_ONLY_SOURCE` (files, fixture). Read
the attributes first and report the before and after values.

## Related
- `aris-process-mining`: analyse the flow these reads return.
- `aris-kg-ingestion`: mirror models into the knowledge graph.
- `aris-epc-to-canonical-workflow`: convert a model to the canonical workflow.
