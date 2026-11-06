"""Surface contracts of aris-mcp: tool use, links, data locations and roles.

Each business task is the ordered tool calls a proven workflow uses: check the
source, read a process model, convert an EPC to the canonical workflow and back,
export AML, ingest into the graph, and enrich a model. Every served tool is
called by a contract step and named by a link. Served as
``ontology://aris-mcp/contracts.ttl``.
"""

# ruff: noqa: E501
from __future__ import annotations

from aris_mcp._surface import (
    BusinessRole,
    DataLocation,
    Refusal,
    SurfaceLink,
    ToolStep,
    ToolUseContract,
)

OPERATOR = "aris-process-operator"
MODELER = "aris-process-modeler"

_NOT_CONFIGURED = Refusal(
    "ARIS_NOT_CONFIGURED",
    "neither ARIS_API_BASE nor ARIS_REPOSITORY_DIR is set; the remedy names both",
)
_NOT_FOUND = Refusal("ARIS_MODEL_NOT_FOUND", "no model has the given guid")
_API = Refusal(
    "ARIS_API_ERROR",
    "the live tenant failed or rejected the call; the message names why",
)
_READ_ONLY = Refusal(
    "ARIS_READ_ONLY_SOURCE", "the repository is a file or fixture repository"
)
_WRITE_DISABLED = Refusal(
    "ARIS_WRITE_DISABLED", "the live tenant is used without ARIS_ENABLE_WRITE=true"
)
_AML_INVALID = Refusal(
    "AML_INVALID",
    "the AML is malformed, too large, or declares a DOCTYPE or entities",
)
_LOSSY = Refusal(
    "PROCESS_EXPORT_LOSSY",
    "strict=true and EPC cannot express a construct; details list the losses",
)
_CANONICAL_INVALID = Refusal(
    "PROCESS_CANONICAL_INVALID",
    "the document is not a medulla.process.canonical/v1 workflow or its digest is wrong",
)
_UNMAPPED = Refusal(
    "PROCESS_IMPORT_UNMAPPED_ELEMENT",
    "a rule operator has a symbol the ontology does not map",
)

CONTRACTS = (
    ToolUseContract(
        "verify-process-source",
        (
            ToolStep(
                "aris_get_source_status",
                result=("mode", "repository", "model_count", "writes_enabled"),
            ),
            ToolStep(
                "aris_list_models",
                params=("limit",),
                result=("repository", "count", "items"),
                refusals=(_NOT_CONFIGURED, _API),
            ),
        ),
        "Check which repository the connector serves (live, files, fixture or unconfigured) and that it answers.",
    ),
    ToolUseContract(
        "read-process-model",
        (
            ToolStep(
                "aris_list_models",
                params=("name", "limit", "offset"),
                result=("items",),
                refusals=(_NOT_CONFIGURED, _API),
            ),
            ToolStep(
                "aris_get_model",
                params=("model_id",),
                result=("model",),
                refusals=(_NOT_CONFIGURED, _NOT_FOUND, _API),
            ),
            ToolStep(
                "aris_list_model_objects",
                params=("model_id",),
                result=("items",),
                refusals=(_NOT_FOUND,),
            ),
            ToolStep(
                "aris_list_model_connections",
                params=("model_id",),
                result=("items",),
                refusals=(_NOT_FOUND,),
            ),
            ToolStep(
                "aris_get_model_attributes",
                params=("model_id",),
                result=("attributes",),
                refusals=(_NOT_FOUND,),
            ),
        ),
        "Find a model and read its objects, connections and attributes.",
    ),
    ToolUseContract(
        "convert-epc-to-canonical-workflow",
        (
            ToolStep(
                "aris_import_aml",
                params=("aml_text", "aml_b64"),
                result=("models",),
                refusals=(_AML_INVALID,),
            ),
            ToolStep(
                "aris_export_canonical_workflow",
                params=("model_id", "aml_text", "aml_b64"),
                result=(
                    "schema",
                    "steps",
                    "flows",
                    "digest",
                    "source",
                    "annex",
                    "losses",
                ),
                refusals=(_AML_INVALID, _UNMAPPED, _NOT_CONFIGURED),
            ),
        ),
        "Turn an ARIS EPC (an AML export or a repository model) into the canonical workflow the engine builds the agent workflow graph from.",
    ),
    ToolUseContract(
        "convert-canonical-to-epc",
        (
            ToolStep(
                "aris_import_canonical_workflow",
                params=("canonical", "strict"),
                result=("model", "objects", "connections", "aml", "losses"),
                refusals=(_LOSSY, _CANONICAL_INVALID),
            ),
        ),
        "Render a canonical workflow (from a BPMN process or an EPC) as an EPC model and AML, listing what EPC cannot express.",
    ),
    ToolUseContract(
        "export-model-aml",
        (
            ToolStep(
                "aris_export_aml",
                params=("model_id",),
                result=("aml",),
                refusals=(_NOT_CONFIGURED, _NOT_FOUND),
            ),
        ),
        "Export one repository model as AML text.",
    ),
    ToolUseContract(
        "ingest-process-models",
        (
            ToolStep(
                "aris_ingest_model_inventory",
                params=("name",),
                result=("listed", "ingested"),
                refusals=(_NOT_CONFIGURED, _API),
            ),
            ToolStep(
                "aris_ingest_model_graph",
                params=("model_id",),
                result=("objects", "connections", "ingested"),
                refusals=(_NOT_CONFIGURED, _NOT_FOUND),
            ),
            ToolStep(
                "aris_ingest_model_export",
                params=("model_id", "data_b64", "mime_type", "export_format"),
                result=("size_bytes", "ingested"),
                refusals=(Refusal("EXPORT_INVALID", "data_b64 is not base64"),),
            ),
        ),
        "Mirror the model inventory, one model's typed EPC graph and a raw export into the knowledge graph.",
    ),
    ToolUseContract(
        "enrich-model-attributes",
        (
            ToolStep(
                "aris_get_model_attributes",
                params=("model_id",),
                result=("attributes",),
                refusals=(_NOT_CONFIGURED, _NOT_FOUND),
            ),
            ToolStep(
                "aris_set_model_attributes",
                params=("model_id", "attributes"),
                result=("result",),
                refusals=(_WRITE_DISABLED, _READ_ONLY, _NOT_CONFIGURED),
            ),
            ToolStep(
                "aris_set_object_attributes",
                params=("object_id", "attributes"),
                result=("result",),
                refusals=(_WRITE_DISABLED, _READ_ONLY, _NOT_CONFIGURED),
            ),
        ),
        "Write graph findings back onto a model or object of the live tenant, reading the current attributes first.",
    ),
)

LINKS = (
    SurfaceLink(
        "verify-process-source",
        tools=("aris_get_source_status", "aris_list_models"),
        prompts=(OPERATOR,),
        skills=("aris-process-modeling", "aris-mcp-development"),
    ),
    SurfaceLink(
        "read-process-model",
        tools=(
            "aris_list_models",
            "aris_get_model",
            "aris_list_model_objects",
            "aris_list_model_connections",
            "aris_get_model_attributes",
        ),
        prompts=(OPERATOR, MODELER),
        skills=("aris-process-modeling", "aris-process-mining"),
    ),
    SurfaceLink(
        "convert-epc-to-canonical-workflow",
        tools=("aris_import_aml", "aris_export_canonical_workflow"),
        prompts=(MODELER, OPERATOR),
        skills=("aris-epc-to-canonical-workflow",),
    ),
    SurfaceLink(
        "convert-canonical-to-epc",
        tools=("aris_import_canonical_workflow",),
        prompts=(MODELER,),
        skills=("aris-epc-to-canonical-workflow",),
    ),
    SurfaceLink(
        "export-model-aml",
        tools=("aris_export_aml",),
        prompts=(MODELER, OPERATOR),
        skills=("aris-process-modeling",),
    ),
    SurfaceLink(
        "ingest-process-models",
        tools=(
            "aris_ingest_model_inventory",
            "aris_ingest_model_graph",
            "aris_ingest_model_export",
        ),
        prompts=(OPERATOR,),
        skills=("aris-kg-ingestion",),
    ),
    SurfaceLink(
        "enrich-model-attributes",
        tools=(
            "aris_get_model_attributes",
            "aris_set_model_attributes",
            "aris_set_object_attributes",
        ),
        prompts=(OPERATOR,),
        skills=("aris-process-modeling",),
    ),
)

_REPOSITORY = "ARIS_API_BASE tenant, else the ARIS_REPOSITORY_DIR AML directory or the bundled fixture repository"

LOCATIONS = (
    DataLocation(
        "process-repository",
        ("EpcModel", "ProcessModel"),
        _REPOSITORY,
        "aris_list_models",
        store="repository",
        route_param="model_id",
        federation_key="guid",
    ),
    DataLocation(
        "process-model-graph",
        (
            "EpcHumanFunction",
            "EpcAutomatedFunction",
            "EpcDecisionFunction",
            "EpcProcessInterface",
            "EpcStartEvent",
            "EpcEndEvent",
            "EpcIntermediateEvent",
            "EpcAndOperator",
            "EpcOrOperator",
            "EpcXorOperator",
            "EpcAttachment",
            "EpcConnection",
        ),
        _REPOSITORY,
        "aris_list_model_objects",
        store="repository",
        route_param="model_id",
        federation_key="guid",
    ),
    DataLocation(
        "canonical-workflow",
        ("ProcessModel",),
        "computed from the EPC model; the engine stores it as the one process model",
        "aris_export_canonical_workflow",
        store="engine",
        route_param="model_id",
        federation_key="digest",
    ),
    DataLocation(
        "model-exports",
        ("AmlDocument", "ModelExport"),
        _REPOSITORY,
        "aris_export_aml",
        store="repository",
        route_param="model_id",
        federation_key="guid",
    ),
)

ROLES = (
    BusinessRole(
        "process-modeler",
        tasks=(
            "read-process-model",
            "convert-epc-to-canonical-workflow",
            "convert-canonical-to-epc",
            "export-model-aml",
        ),
        description="Turns business procedures into EPC models and converts between EPC, the canonical workflow and BPMN.",
    ),
)
