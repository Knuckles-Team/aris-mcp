"""ARIS tools: one typed tool per operation.

Every repository tool resolves the current source (:mod:`aris_mcp.source`):
the live REST tenant, a directory of AML exports, or the bundled fixture
repository. With no source configured a repository tool refuses
``ARIS_NOT_CONFIGURED``; writes to a file or fixture repository refuse
``ARIS_READ_ONLY_SOURCE``; live writes refuse ``ARIS_WRITE_DISABLED`` unless
``ARIS_ENABLE_WRITE`` is set. A refusal is returned as an ``isError`` result
whose structured content is ``{"refused": true, "code", "message", "remedy"}``.

The conversion tools (AML import/export, canonical workflow import/export) work
on AML text without any repository.
"""

from __future__ import annotations

import base64
import binascii
import json
from functools import cache
from importlib import resources
from typing import Annotated, Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from aris_mcp.aml import AmlError, AmlModel, read_aml, write_aml
from aris_mcp.canonical import CanonicalError, canonical_to_epc, epc_to_canonical
from aris_mcp.source import (
    LIVE,
    ArisRefusal,
    get_source,
    refusals_as_results,
    source_status,
    write_disabled,
)

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
CONVERT = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
INGEST = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)

ModelId = Annotated[str, Field(description="Model GUID (or AML Model.ID).")]


def _writes_enabled() -> bool:
    from aris_mcp.source import writes_enabled

    return writes_enabled()


def _records(result: Any) -> list[dict[str, Any]]:
    """A list of record dicts from a list or an ``items``/``data`` envelope."""
    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    if isinstance(result, dict):
        for key in ("items", "results", "data", "models", "objects", "connections"):
            if isinstance(result.get(key), list):
                return [r for r in result[key] if isinstance(r, dict)]
    return []


def _call(fn: Any, *args: Any) -> Any:
    """Run one repository call; map transport failures to typed refusals."""
    try:
        return fn(*args)
    except ArisRefusal:
        raise
    except PermissionError as exc:
        raise write_disabled() from exc
    except Exception as exc:  # noqa: BLE001 - surfaced as a typed refusal
        raise ArisRefusal(
            "ARIS_API_ERROR",
            f"The ARIS repository call failed: {exc}",
            "Check ARIS_API_BASE, the credentials and ARIS_PATHS_JSON for this tenant.",
        ) from exc


def _model_bundle(model_id: str) -> tuple[str, AmlModel]:
    mode, repo = get_source()
    model = _call(repo.get_model, model_id)
    model = model if isinstance(model, dict) else {"guid": model_id}
    objects = _records(_call(repo.list_model_objects, model_id))
    connections = _records(_call(repo.list_model_connections, model_id))
    return mode, AmlModel(model, objects, connections)


def _aml_bytes(aml_text: str | None, aml_b64: str | None) -> bytes:
    if aml_text:
        return aml_text.encode("utf-8")
    if aml_b64:
        try:
            return base64.b64decode(aml_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ArisRefusal(
                "AML_INVALID", "aml_b64 is not valid base64.", "Pass aml_text instead."
            ) from exc
    raise ArisRefusal(
        "AML_MISSING",
        "No AML document was given.",
        "Pass aml_text (the AML XML) or aml_b64 (its base64 bytes).",
    )


def _read(data: bytes) -> list[AmlModel]:
    try:
        return read_aml(data)
    except AmlError as exc:
        raise ArisRefusal(
            "AML_INVALID",
            str(exc),
            "Pass an ARIS AML export without a DOCTYPE or entity declarations.",
        ) from exc


def _pick(models: list[AmlModel], model_id: str | None) -> AmlModel:
    if not models:
        raise ArisRefusal(
            "AML_NO_MODEL", "The AML document holds no model.", "Export a model."
        )
    if model_id:
        for bundle in models:
            if model_id in (bundle.model.get("guid"), bundle.model.get("id")):
                return bundle
        raise ArisRefusal(
            "ARIS_MODEL_NOT_FOUND",
            f"No model {model_id!r} in the AML document.",
            "Pass the guid of one of its models, or omit model_id for the first.",
        )
    return models[0]


def _canonical_refusal(exc: CanonicalError) -> ArisRefusal:
    remedy = {
        "PROCESS_EXPORT_LOSSY": "Call again with strict=false to export and list the losses.",
        "PROCESS_CANONICAL_INVALID": "Pass a medulla.process.canonical/v1 document.",
    }.get(exc.code, "Fix the named element and call again.")
    return ArisRefusal(exc.code, exc.message, remedy, exc.details)


@cache
def contracts_turtle() -> str:
    """The surface declarations of ``aris_mcp.connector_contracts`` as Turtle."""
    from aris_mcp import connector_contracts as declared
    from aris_mcp._surface import render_surface_turtle

    prompts: dict[str, dict[str, Any]] = {}
    for path in sorted((resources.files("aris_mcp") / "prompts").iterdir()):
        if path.name.endswith(".json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            prompts[path.name[: -len(".json")]] = document.get("agent") or {}
    return render_surface_turtle(
        "aris-mcp",
        declared.CONTRACTS,
        declared.LINKS,
        declared.LOCATIONS,
        declared.ROLES,
        prompts,
    )


def register_aris_tools(mcp: FastMCP) -> None:
    """Register the ARIS repository, conversion and ingest tools."""

    @mcp.resource(
        "ontology://aris-mcp/contracts.ttl",
        name="aris-mcp-contracts",
        description=(
            "Tool-use contracts, prompt/skill/tool links, data locations and "
            "business roles of aris-mcp, as surface-contract Turtle."
        ),
        mime_type="text/turtle",
    )
    def aris_contracts() -> str:
        return contracts_turtle()

    @mcp.tool(tags={"source"}, annotations=READ)
    @refusals_as_results
    def aris_get_source_status() -> dict[str, Any]:
        """Report where the ARIS repository comes from.

        Returns ``mode`` (live, files, fixture or unconfigured), ``repository``
        (the API base or the AML directory), ``model_count`` (files and fixture
        modes) and ``writes_enabled``.
        """
        return source_status()

    @mcp.tool(tags={"model"}, annotations=READ)
    @refusals_as_results
    def aris_list_models(
        name: Annotated[
            str | None, Field(description="Only models whose name contains this.")
        ] = None,
        limit: Annotated[int | None, Field(ge=1, description="Page size.")] = None,
        offset: Annotated[int | None, Field(ge=0, description="Page offset.")] = None,
    ) -> dict[str, Any]:
        """List the models of the repository (guid, name, type, group path)."""
        mode, repo = get_source()
        params = {
            k: v
            for k, v in (("name", name), ("limit", limit), ("offset", offset))
            if v is not None
        }
        items = _records(_call(repo.list_models, params or None))
        return {"repository": mode, "count": len(items), "items": items}

    @mcp.tool(tags={"model"}, annotations=READ)
    @refusals_as_results
    def aris_get_model(model_id: ModelId) -> dict[str, Any]:
        """Get one model's record (guid, name, type, group path, attributes)."""
        mode, repo = get_source()
        return {"repository": mode, "model": _call(repo.get_model, model_id)}

    @mcp.tool(tags={"model"}, annotations=READ)
    @refusals_as_results
    def aris_list_model_objects(model_id: ModelId) -> dict[str, Any]:
        """List the objects placed on a model: functions, events, rule operators
        and attached objects, each with its ARIS type (TypeNum) and symbol."""
        mode, repo = get_source()
        items = _records(_call(repo.list_model_objects, model_id))
        return {"repository": mode, "model_id": model_id, "items": items}

    @mcp.tool(tags={"model"}, annotations=READ)
    @refusals_as_results
    def aris_list_model_connections(model_id: ModelId) -> dict[str, Any]:
        """List the directed connections of a model (sourceObjectId ->
        targetObjectId with the connection type)."""
        mode, repo = get_source()
        items = _records(_call(repo.list_model_connections, model_id))
        return {"repository": mode, "model_id": model_id, "items": items}

    @mcp.tool(tags={"model"}, annotations=READ)
    @refusals_as_results
    def aris_get_model_attributes(model_id: ModelId) -> dict[str, Any]:
        """Get a model's attributes (for example AT_NAME and kg_intelligence)."""
        mode, repo = get_source()
        result = _call(repo.list_model_attributes, model_id)
        return {"repository": mode, "model_id": model_id, "attributes": result}

    @mcp.tool(tags={"model", "write"}, annotations=WRITE)
    @refusals_as_results
    def aris_set_model_attributes(
        model_id: ModelId,
        attributes: Annotated[
            dict[str, str], Field(description="Attribute type -> value to write.")
        ],
    ) -> dict[str, Any]:
        """Write attributes on a model of the live tenant (needs ARIS_ENABLE_WRITE)."""
        mode, repo = get_source()
        if mode == LIVE and not _writes_enabled():
            raise write_disabled()
        result = _call(repo.set_model_attributes, model_id, attributes)
        return {"repository": mode, "model_id": model_id, "result": result}

    @mcp.tool(tags={"object", "write"}, annotations=WRITE)
    @refusals_as_results
    def aris_set_object_attributes(
        object_id: Annotated[str, Field(description="Object GUID.")],
        attributes: Annotated[
            dict[str, str], Field(description="Attribute type -> value to write.")
        ],
    ) -> dict[str, Any]:
        """Write attributes on one object of the live tenant (needs ARIS_ENABLE_WRITE)."""
        mode, repo = get_source()
        if mode == LIVE and not _writes_enabled():
            raise write_disabled()
        result = _call(repo.set_object_attributes, object_id, attributes)
        return {"repository": mode, "object_id": object_id, "result": result}

    @mcp.tool(tags={"model", "kg"}, annotations=INGEST)
    @refusals_as_results
    async def aris_ingest_model_inventory(
        name: Annotated[
            str | None, Field(description="Only models whose name contains this.")
        ] = None,
    ) -> dict[str, Any]:
        """Ingest the model inventory into the knowledge graph as model nodes.

        Best-effort: ``ingested`` is ``null`` when no engine is reachable.
        CONCEPT:AU-KG.ingest.enterprise-source-extractor.
        """
        from aris_mcp.kg_ingest import ingest_models

        mode, repo = get_source()
        models = _records(_call(repo.list_models, {"name": name} if name else None))
        return {
            "repository": mode,
            "listed": len(models),
            "ingested": await ingest_models(models),
        }

    @mcp.tool(tags={"model", "kg"}, annotations=INGEST)
    @refusals_as_results
    async def aris_ingest_model_graph(model_id: ModelId) -> dict[str, Any]:
        """Ingest one model with its objects (typed by their leaf ontology class)
        and its connections (reified, plus :flowsTo) into the knowledge graph."""
        from aris_mcp.kg_ingest import ingest_model_graph

        mode, bundle = _model_bundle(model_id)
        result = await ingest_model_graph(
            bundle.model, bundle.objects, bundle.connections
        )
        return {
            "repository": mode,
            "model_id": model_id,
            "objects": len(bundle.objects),
            "connections": len(bundle.connections),
            "ingested": result,
        }

    @mcp.tool(tags={"model", "kg"}, annotations=INGEST)
    @refusals_as_results
    async def aris_ingest_model_export(
        model_id: ModelId,
        data_b64: Annotated[str, Field(description="The export bytes, base64.")],
        mime_type: Annotated[
            str, Field(description="MIME type of the export.")
        ] = "application/xml",
        model_name: Annotated[str, Field(description="Model name.")] = "",
        export_format: Annotated[
            str, Field(description="aml, bpmn, xml, svg or pdf.")
        ] = "",
    ) -> dict[str, Any]:
        """Store a raw model export as a content-addressed knowledge-graph blob.

        Best-effort: ``ingested`` is ``null`` when no engine is reachable.
        CONCEPT:AU-KG.ingest.list-durable-media.
        """
        from aris_mcp.kg_media import ingest_model_export

        try:
            data = base64.b64decode(data_b64, validate=True) if data_b64 else b""
        except (binascii.Error, ValueError) as exc:
            raise ArisRefusal(
                "EXPORT_INVALID", "data_b64 is not valid base64.", "Re-encode it."
            ) from exc
        result = await ingest_model_export(
            data,
            model_id=model_id,
            model_name=model_name,
            mime_type=mime_type,
            export_format=export_format,
        )
        return {"model_id": model_id, "size_bytes": len(data), "ingested": result}

    @mcp.tool(tags={"aml"}, annotations=INGEST)
    @refusals_as_results
    async def aris_import_aml(
        aml_text: Annotated[
            str | None, Field(description="An ARIS AML export (XML text).")
        ] = None,
        aml_b64: Annotated[
            str | None, Field(description="The same, as base64 bytes.")
        ] = None,
        ingest: Annotated[
            bool, Field(description="Also ingest every model into the graph.")
        ] = False,
    ) -> dict[str, Any]:
        """Read an AML export into model, object and connection records (the
        shapes the read tools return); optionally ingest each model."""
        models = _read(_aml_bytes(aml_text, aml_b64))
        out: dict[str, Any] = {
            "models": [
                {
                    "model": b.model,
                    "objects": b.objects,
                    "connections": b.connections,
                }
                for b in models
            ]
        }
        if ingest:
            from aris_mcp.kg_ingest import ingest_model_graph

            out["ingested"] = [
                await ingest_model_graph(b.model, b.objects, b.connections)
                for b in models
            ]
        return out

    @mcp.tool(tags={"aml"}, annotations=READ)
    @refusals_as_results
    def aris_export_aml(model_id: ModelId) -> dict[str, Any]:
        """Export one model of the current repository as AML text."""
        mode, bundle = _model_bundle(model_id)
        return {"repository": mode, "model_id": model_id, "aml": write_aml([bundle])}

    @mcp.tool(tags={"canonical"}, annotations=CONVERT)
    @refusals_as_results
    def aris_export_canonical_workflow(
        model_id: Annotated[
            str | None,
            Field(
                description=(
                    "Model GUID: read from the current repository, or picks the "
                    "model of the given AML (default: its first model)."
                )
            ),
        ] = None,
        aml_text: Annotated[
            str | None, Field(description="An AML export to convert instead.")
        ] = None,
        aml_b64: Annotated[
            str | None, Field(description="The same, as base64 bytes.")
        ] = None,
    ) -> dict[str, Any]:
        """Convert an EPC model to the canonical workflow
        (medulla.process.canonical/v1): steps, flows, digest, source, annex and
        losses. The agent workflow graph is built from this form."""
        if aml_text or aml_b64:
            bundle = _pick(_read(_aml_bytes(aml_text, aml_b64)), model_id)
        elif model_id:
            _mode, bundle = _model_bundle(model_id)
        else:
            raise ArisRefusal(
                "MODEL_REQUIRED",
                "Neither model_id nor an AML document was given.",
                "Pass model_id (from aris_list_models) or aml_text.",
            )
        try:
            return epc_to_canonical(bundle.model, bundle.objects, bundle.connections)
        except CanonicalError as exc:
            raise _canonical_refusal(exc) from exc

    @mcp.tool(tags={"canonical"}, annotations=CONVERT)
    @refusals_as_results
    def aris_import_canonical_workflow(
        canonical: Annotated[
            dict[str, Any],
            Field(description="A medulla.process.canonical/v1 document."),
        ],
        strict: Annotated[
            bool,
            Field(
                description=(
                    "Refuse PROCESS_EXPORT_LOSSY instead of exporting when EPC "
                    "cannot express a construct."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Convert a canonical workflow to EPC records and AML text, listing
        what EPC cannot express as losses. Writes nothing to the repository."""
        try:
            epc = canonical_to_epc(canonical, strict=strict)
        except CanonicalError as exc:
            raise _canonical_refusal(exc) from exc
        bundle = AmlModel(epc["model"], epc["objects"], epc["connections"])
        return {**epc, "aml": write_aml([bundle])}
