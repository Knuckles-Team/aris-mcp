"""ARIS Markup Language (AML) reader and writer.

The reader turns an AML export (``Group``/``ObjDef``/``CxnDef``/``Model``/
``ObjOcc``/``CxnOcc`` with ``AttrDef``, ``TypeNum``/``SymbolNum`` and ``GUID``)
into the same record shapes the live REST client returns, so a repository served
from files and the live tenant are interchangeable behind one interface:

* model: ``{"guid", "id", "name", "type", "groupPath", "attributes"}``
* object: ``{"guid", "id", "name", "type", "symbol", "attributes"}``
* connection: ``{"guid", "id", "type", "sourceObjectId", "targetObjectId"}``

Parsing refuses a document type declaration and entity declarations (no DTD, no
entity expansion, no external references) and documents above a size limit. The
writer produces AML the reader reads back to the same records.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # noqa: S405 - only used to build, never to parse
from dataclasses import dataclass, field
from typing import Any

from defusedxml import DefusedXmlException
from defusedxml import ElementTree as SafeET

MAX_AML_BYTES = 16 * 1024 * 1024
DEFAULT_LOCALE = "1033"


class AmlError(ValueError):
    """An AML document that cannot be read (malformed, refused or too large)."""


@dataclass
class AmlModel:
    """One model of an AML document with its objects and connections."""

    model: dict[str, Any]
    objects: list[dict[str, Any]] = field(default_factory=list)
    connections: list[dict[str, Any]] = field(default_factory=list)


# ── reading ────────────────────────────────────────────────────────────────


def _guid(elem: ET.Element) -> str | None:
    node = elem.find("GUID")
    text = (node.text or "").strip() if node is not None else ""
    return text or None


def _attr_text(attr_def: ET.Element) -> str:
    value = attr_def.find("AttrValue")
    if value is None:
        return ""
    plain = [p.get("TextValue", "") for p in value.iter("PlainText")]
    if plain:
        return "".join(plain)
    return "".join(value.itertext()).strip()


def _attributes(elem: ET.Element) -> dict[str, str]:
    return {
        a.get("AttrDef.Type", ""): _attr_text(a)
        for a in elem.findall("AttrDef")
        if a.get("AttrDef.Type")
    }


def _parse(data: str | bytes) -> ET.Element:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    if len(raw) > MAX_AML_BYTES:
        raise AmlError(f"AML document exceeds {MAX_AML_BYTES} bytes")
    try:
        root = SafeET.fromstring(raw, forbid_dtd=True)
    except DefusedXmlException as exc:
        raise AmlError(f"AML document refused: {type(exc).__name__}") from exc
    except ET.ParseError as exc:
        raise AmlError(f"AML document is not well-formed XML: {exc}") from exc
    if root.tag != "AML":
        raise AmlError(f"not an AML document (root element {root.tag!r})")
    return root


def _group_paths(root: ET.Element) -> dict[int, str]:
    """The slash-joined group path of every ``Group`` element, by ``id()``."""
    paths: dict[int, str] = {}

    def walk(elem: ET.Element, prefix: str) -> None:
        for group in elem.findall("Group"):
            name = _attributes(group).get("AT_NAME", "")
            path = f"{prefix}/{name}" if prefix and name else (name or prefix)
            paths[id(group)] = path
            walk(group, path)

    database = root.find("Database")
    walk(database if database is not None else root, "")
    return paths


def read_aml(data: str | bytes) -> list[AmlModel]:
    """Every model of an AML document as live-client record shapes."""
    root = _parse(data)
    group_paths = _group_paths(root)

    defs: dict[str, ET.Element] = {}
    cxn_defs: dict[str, tuple[ET.Element, str]] = {}
    for group in root.iter("Group"):
        for obj in group.findall("ObjDef"):
            defs[obj.get("ObjDef.ID", "")] = obj
            for cxn in obj.findall("CxnDef"):
                cxn_defs[cxn.get("CxnDef.ID", "")] = (cxn, obj.get("ObjDef.ID", ""))

    def obj_guid(def_id: str) -> str:
        elem = defs.get(def_id)
        return (_guid(elem) if elem is not None else None) or def_id

    models: list[AmlModel] = []
    for group in root.iter("Group"):
        for model in group.findall("Model"):
            attrs = _attributes(model)
            model_id = model.get("Model.ID", "")
            record = AmlModel(
                model={
                    "guid": _guid(model) or model_id,
                    "id": model_id,
                    "name": attrs.get("AT_NAME", ""),
                    "type": model.get("Model.Type", ""),
                    "groupPath": group_paths.get(id(group), ""),
                    "attributes": attrs,
                }
            )
            occ_def: dict[str, str] = {}
            seen: set[str] = set()
            for occ in model.findall("ObjOcc"):
                def_id = occ.get("ObjDef.IdRef", "")
                occ_def[occ.get("ObjOcc.ID", "")] = def_id
                obj = defs.get(def_id)
                if obj is None or def_id in seen:
                    continue
                seen.add(def_id)
                obj_attrs = _attributes(obj)
                record.objects.append(
                    {
                        "guid": obj_guid(def_id),
                        "id": def_id,
                        "name": obj_attrs.get("AT_NAME", ""),
                        "type": obj.get("TypeNum", ""),
                        "symbol": occ.get("SymbolNum") or obj.get("SymbolNum", ""),
                        "attributes": obj_attrs,
                    }
                )
            for occ in model.findall("ObjOcc"):
                for cxn_occ in occ.findall("CxnOcc"):
                    found = cxn_defs.get(cxn_occ.get("CxnDef.IdRef", ""))
                    target_def = occ_def.get(cxn_occ.get("ToObjOcc.IdRef", ""))
                    if found is None or target_def is None:
                        continue
                    cxn, source_def = found
                    cxn_id = cxn.get("CxnDef.ID", "")
                    record.connections.append(
                        {
                            "guid": _guid(cxn) or cxn_id,
                            "id": cxn_id,
                            "type": cxn.get("CxnDef.Type", ""),
                            "sourceObjectId": obj_guid(source_def),
                            "targetObjectId": obj_guid(target_def),
                        }
                    )
            models.append(record)
    return models


# ── writing ────────────────────────────────────────────────────────────────


def _safe_id(prefix: str, value: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(value))
    return f"{prefix}.{cleaned}"


def _add_guid(parent: ET.Element, guid: str | None) -> None:
    if guid:
        ET.SubElement(parent, "GUID").text = guid


def _add_attrs(parent: ET.Element, attrs: dict[str, Any], name: str) -> None:
    merged = {"AT_NAME": name, **{k: v for k, v in attrs.items() if k != "AT_NAME"}}
    for attr_type, value in merged.items():
        if value is None:
            continue
        attr = ET.SubElement(parent, "AttrDef", {"AttrDef.Type": attr_type})
        val = ET.SubElement(attr, "AttrValue", {"LocaleId": DEFAULT_LOCALE})
        val.text = str(value)


def write_aml(models: list[AmlModel], *, database: str = "aris-mcp") -> str:
    """AML text holding ``models`` (records as :func:`read_aml` returns them)."""
    root = ET.Element("AML")
    ET.SubElement(root, "Header-Info", {"DatabaseName": database})
    ET.SubElement(root, "Language", {"LocaleId": DEFAULT_LOCALE})
    db = ET.SubElement(root, "Database")
    group = ET.SubElement(db, "Group", {"Group.ID": "Group.Root"})
    groups: dict[str, ET.Element] = {}

    def group_for(path: str) -> ET.Element:
        """The group element of a slash-joined path, created on first use.

        The first path's first segment names the root group; any other path
        is filed beneath the root.
        """
        parts = [p for p in (path or "Main group").split("/") if p]
        if not groups:
            _add_attrs(group, {}, parts[0])
            groups[parts[0]] = group
        root_name = next(iter(groups))
        if parts[0] != root_name:
            parts = [root_name, *parts]
        key, parent = root_name, group
        for part in parts[1:]:
            key = f"{key}/{part}"
            if key not in groups:
                child = ET.SubElement(
                    parent, "Group", {"Group.ID": _safe_id("Group", key)}
                )
                _add_attrs(child, {}, part)
                groups[key] = child
            parent = groups[key]
        return parent

    def_ids: dict[str, str] = {}
    def_elems: dict[str, ET.Element] = {}
    for bundle in models:
        for obj in bundle.objects:
            guid = str(obj.get("guid") or obj.get("id"))
            if guid in def_ids:
                continue
            def_id = str(obj.get("id") or _safe_id("ObjDef", guid))
            if not def_id.startswith("ObjDef."):
                def_id = _safe_id("ObjDef", def_id)
            def_ids[guid] = def_id
            attrs = {
                "ObjDef.ID": def_id,
                "TypeNum": str(obj.get("type", "")),
            }
            if obj.get("symbol"):
                attrs["SymbolNum"] = str(obj["symbol"])
            elem = ET.SubElement(group, "ObjDef", attrs)
            _add_guid(elem, guid)
            _add_attrs(elem, dict(obj.get("attributes") or {}), obj.get("name", ""))
            def_elems[guid] = elem

    cxn_ids: dict[str, str] = {}
    for bundle in models:
        for cxn in bundle.connections:
            guid = str(cxn.get("guid") or cxn.get("id"))
            if guid in cxn_ids:
                continue
            source = def_elems.get(str(cxn["sourceObjectId"]))
            target = def_ids.get(str(cxn["targetObjectId"]))
            if source is None or target is None:
                continue
            cxn_id = str(cxn.get("id") or _safe_id("CxnDef", guid))
            if not cxn_id.startswith("CxnDef."):
                cxn_id = _safe_id("CxnDef", cxn_id)
            cxn_ids[guid] = cxn_id
            elem = ET.SubElement(
                source,
                "CxnDef",
                {
                    "CxnDef.ID": cxn_id,
                    "CxnDef.Type": str(cxn.get("type", "")),
                    "ToObjDef.IdRef": target,
                },
            )
            _add_guid(elem, guid)

    for index, bundle in enumerate(models, start=1):
        model = bundle.model
        model_id = str(model.get("id") or f"Model.{index}")
        if not model_id.startswith("Model."):
            model_id = _safe_id("Model", model_id)
        elem = ET.SubElement(
            group_for(str(model.get("groupPath") or "")),
            "Model",
            {"Model.ID": model_id, "Model.Type": str(model.get("type", "MT_EEPC"))},
        )
        _add_guid(elem, str(model.get("guid") or model_id))
        _add_attrs(elem, dict(model.get("attributes") or {}), model.get("name", ""))
        occ_ids: dict[str, str] = {}
        occ_elems: dict[str, ET.Element] = {}
        for n, obj in enumerate(bundle.objects, start=1):
            guid = str(obj.get("guid") or obj.get("id"))
            occ_id = f"ObjOcc.{index}.{n}"
            occ_ids[guid] = occ_id
            attrs = {"ObjOcc.ID": occ_id, "ObjDef.IdRef": def_ids[guid]}
            if obj.get("symbol"):
                attrs["SymbolNum"] = str(obj["symbol"])
            occ = ET.SubElement(elem, "ObjOcc", attrs)
            ET.SubElement(occ, "Position", {"Pos.X": str(100 * n), "Pos.Y": "100"})
            occ_elems[guid] = occ
        for n, cxn in enumerate(bundle.connections, start=1):
            guid = str(cxn.get("guid") or cxn.get("id"))
            source = occ_elems.get(str(cxn["sourceObjectId"]))
            target = occ_ids.get(str(cxn["targetObjectId"]))
            if source is None or target is None or guid not in cxn_ids:
                continue
            ET.SubElement(
                source,
                "CxnOcc",
                {
                    "CxnOcc.ID": f"CxnOcc.{index}.{n}",
                    "CxnDef.IdRef": cxn_ids[guid],
                    "ToObjOcc.IdRef": target,
                },
            )

    ET.indent(root)
    body = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"
