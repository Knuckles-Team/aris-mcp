"""EPC <-> canonical workflow (``medulla.process.canonical/v1``) adapter.

An ARIS EPC and a BPMN 2.0 process map to ONE canonical workflow; the agent
workflow graph is built from the canonical form only. This module converts EPC
records (as the live client and the AML reader return them) to the canonical
form and back:

* :func:`epc_to_canonical` folds intermediate events (a condition event after a
  split operator becomes the flow's condition, any other intermediate event goes
  to the annex), classifies functions by their attached objects, numbers the
  steps deterministically and computes the digest over schema, steps and flows.
* :func:`canonical_to_epc` restores EPC alternation, restores annexed events and
  attachments on a same-source export, and lists what EPC cannot express as
  ``losses``; ``strict=True`` refuses ``PROCESS_EXPORT_LOSSY`` instead.

The construct mapping (types, symbols, kinds, gates, attachment roles) comes from
the ontology annotations in ``ontology/aris.ttl`` through
:mod:`aris_mcp.vocabulary`.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from aris_mcp.aml import AmlModel
from aris_mcp.vocabulary import CANONICAL_KINDS, GATES, EpcVocabulary, vocabulary

SCHEMA = "medulla.process.canonical/v1"
SYSTEM = "aris"
_NS = uuid.UUID("6f1d3c52-4b1e-5d7a-9c0e-a215c0de2026")
_FUNCTION_KINDS = frozenset({"human", "agent", "decision", "call"})
_EVENT_KINDS = frozenset({"start", "end", "wait", "boundary"})
_GATE_KINDS = frozenset({"branch", "fork", "join"})


class CanonicalError(ValueError):
    """A typed refusal of the adapter: ``code``, ``message`` and ``details``."""

    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def normalize_text(value: Any) -> str | None:
    """Unicode NFC, whitespace collapsed to single spaces, trimmed; case kept."""
    if value is None:
        return None
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def compute_digest(steps: list[dict[str, Any]], flows: list[dict[str, Any]]) -> str:
    """SHA-256 of the canonical JSON of ``{"schema", "steps", "flows"}``."""
    body = json.dumps(
        {"schema": SCHEMA, "steps": steps, "flows": flows},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


# ── canonical numbering (shared by every reader) ───────────────────────────


@dataclass
class _Node:
    key: str  # source element key, unique within one conversion
    kind: str
    gate: str | None
    label: str
    role: str | None = None
    ref: str | None = None
    element: str = ""


def number_steps(
    nodes: dict[str, _Node], edges: Iterable[tuple[str, str]]
) -> dict[str, int]:
    """Canonical index of every node: Kahn's algorithm with the contract's key.

    Key: (smallest canonical index among already-numbered predecessors, 0 for
    none; kind; gate; label), final tie-break the source element key. When a cycle
    leaves no step whose predecessors are all numbered, the remaining step with
    the fewest unnumbered predecessors is taken under the same key.
    """
    preds: dict[str, set[str]] = defaultdict(set)
    for source, target in edges:
        if source != target:
            preds[target].add(source)
    numbered: dict[str, int] = {}
    remaining = set(nodes)

    def sort_key(key: str) -> tuple[Any, ...]:
        node = nodes[key]
        done = [numbered[p] for p in preds[key] if p in numbered]
        return (min(done, default=0), node.kind, node.gate or "", node.label, key)

    while remaining:
        unnumbered = {
            k: sum(1 for p in preds[k] if p not in numbered) for k in remaining
        }
        fewest = min(unnumbered.values())
        pick = min((k for k in remaining if unnumbered[k] == fewest), key=sort_key)
        numbered[pick] = len(numbered) + 1
        remaining.discard(pick)
    return numbered


def build_canonical(
    name: str,
    nodes: dict[str, _Node],
    flows: Iterable[tuple[str, str, str | None, bool]],
    *,
    system: str,
    model_id: str,
    annex: list[dict[str, Any]] | None = None,
    losses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Number ``nodes``, render steps and flows, and compute the digest.

    ``annex`` entries may carry node keys in ``after``/``before``; they are
    rewritten to canonical ids.
    """
    flow_list = list(flows)
    index = number_steps(nodes, [(s, t) for s, t, _c, _d in flow_list])
    sid = {key: f"s{n}" for key, n in index.items()}
    steps = [
        {
            "id": sid[key],
            "kind": node.kind,
            "gate": node.gate,
            "label": normalize_text(node.label) or "",
            "role": normalize_text(node.role) or None,
            "ref": normalize_text(node.ref) or None,
        }
        for key, node in sorted(nodes.items(), key=lambda kv: index[kv[0]])
    ]
    rendered = {
        (
            index[s],
            index[t],
            normalize_text(c) or "",
            bool(d),
        )
        for s, t, c, d in flow_list
    }
    flow_out = [
        {"source": f"s{s}", "target": f"s{t}", "condition": c or None, "default": d}
        for s, t, c, d in sorted(rendered)
    ]
    out_annex = []
    for entry in annex or []:
        entry = dict(entry)
        for side in ("after", "before"):
            if entry.get(side) in sid:
                entry[side] = sid[entry[side]]
        out_annex.append(entry)
    return {
        "schema": SCHEMA,
        "name": normalize_text(name) or "",
        "steps": steps,
        "flows": flow_out,
        "digest": compute_digest(steps, flow_out),
        "source": {
            "system": system,
            "model_id": model_id,
            "elements": {sid[k]: n.element for k, n in nodes.items()},
        },
        "annex": out_annex,
        "losses": list(losses or []),
    }


# ── EPC -> canonical ───────────────────────────────────────────────────────


def _rid(rec: dict[str, Any]) -> str:
    return str(rec.get("guid") or rec.get("id") or "")


def _endpoints(cxn: dict[str, Any]) -> tuple[str, str]:
    source = (
        cxn.get("sourceObjectId")
        or cxn.get("source")
        or cxn.get("sourceGuid")
        or cxn.get("from")
    )
    target = (
        cxn.get("targetObjectId")
        or cxn.get("target")
        or cxn.get("targetGuid")
        or cxn.get("to")
    )
    return str(source or ""), str(target or "")


def _first_name(objs: list[dict[str, Any]]) -> str | None:
    names = sorted(normalize_text(o.get("name")) or "" for o in objs)
    return names[0] if names else None


@dataclass
class _Epc:
    vocab: EpcVocabulary
    objects: dict[str, dict[str, Any]]
    control: dict[str, str] = field(default_factory=dict)  # guid -> function|event|rule
    succ: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    pred: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    attached: dict[str, list[tuple[dict[str, Any], str]]] = field(
        default_factory=lambda: defaultdict(list)
    )


def _load(objects: list[dict[str, Any]], connections: list[dict[str, Any]]) -> _Epc:
    vocab = vocabulary()
    epc = _Epc(vocab, {_rid(o): o for o in objects if _rid(o)})
    for guid, obj in epc.objects.items():
        type_num = str(obj.get("type") or "")
        if type_num in vocab.function_type_nums:
            epc.control[guid] = "function"
        elif type_num in vocab.event_type_nums:
            epc.control[guid] = "event"
        elif type_num in vocab.rule_type_nums:
            epc.control[guid] = "rule"
    for cxn in connections:
        source, target = _endpoints(cxn)
        if source not in epc.objects or target not in epc.objects:
            continue
        if source in epc.control and target in epc.control:
            if target not in epc.succ[source]:
                epc.succ[source].append(target)
                epc.pred[target].append(source)
            continue
        ctype = str(cxn.get("type") or "")
        if epc.control.get(target) == "function" and source not in epc.control:
            epc.attached[target].append((epc.objects[source], ctype))
        elif epc.control.get(source) == "function" and target not in epc.control:
            epc.attached[source].append((epc.objects[target], ctype))
    for guid in epc.succ:
        epc.succ[guid].sort()
    return epc


def _function_node(epc: _Epc, guid: str, annex: list[dict[str, Any]]) -> _Node:
    obj = epc.objects[guid]
    vocab = epc.vocab
    performers, support, rules = [], [], []
    for att, ctype in sorted(epc.attached[guid], key=lambda a: _rid(a[0])):
        cls = vocab.attachment_class(str(att.get("type") or ""))
        if cls is None:
            annex.append(
                {
                    "after": guid,
                    "construct": "epc-attachment",
                    "element_id": _rid(att),
                    "label": normalize_text(att.get("name")) or "",
                    "type_num": str(att.get("type") or ""),
                }
            )
        elif cls.attachment_role == "performer" and ctype.startswith("CT_EXEC"):
            performers.append(att)
        elif cls.attachment_role == "it-support":
            support.append(att)
        elif cls.attachment_role == "decision-rule":
            rules.append(att)
    label = normalize_text(obj.get("name")) or ""
    role = _first_name(performers)
    if str(obj.get("symbol") or "") in vocab.interface_symbols():
        kind, ref = vocab.by_kind("call").kind, label
    elif rules:
        kind, ref = vocab.by_kind("decision").kind, _first_name(rules)
    elif performers and not support:
        kind, ref = vocab.by_kind("human").kind, None
    else:
        kind, ref = vocab.by_kind("agent").kind, None
    return _Node(guid, str(kind), None, label, role, ref, guid)


def epc_to_canonical(
    model: dict[str, Any],
    objects: list[dict[str, Any]],
    connections: list[dict[str, Any]],
) -> dict[str, Any]:
    """The canonical workflow of one EPC model (records as the client returns)."""
    epc = _load(objects, connections)
    vocab = epc.vocab
    annex: list[dict[str, Any]] = []
    nodes: dict[str, _Node] = {}
    entry: dict[str, str] = {}  # guid -> node key flows arrive at
    exit_: dict[str, str] = {}  # guid -> node key flows leave from
    folded: dict[str, str] = {}  # event guid -> "condition" | "state"
    split_rules: set[str] = set()

    for guid, role in sorted(epc.control.items()):
        obj = epc.objects[guid]
        label = normalize_text(obj.get("name")) or ""
        n_in, n_out = len(epc.pred[guid]), len(epc.succ[guid])
        if role == "function":
            nodes[guid] = _function_node(epc, guid, annex)
            entry[guid] = exit_[guid] = guid
        elif role == "rule":
            cls = vocab.gate_for_symbol(str(obj.get("symbol") or ""))
            if cls is None:
                raise CanonicalError(
                    "PROCESS_IMPORT_UNMAPPED_ELEMENT",
                    f"rule operator {guid} has no mapped symbol",
                    {"element": guid, "symbol": obj.get("symbol")},
                )
            gate, split_kind = cls.gate, str(cls.kind)
            if n_out >= 2:
                split_rules.add(guid)
            if n_in >= 2 and n_out >= 2:
                join_key, split_key = f"{guid}#join", f"{guid}#split"
                nodes[join_key] = _Node(join_key, "join", gate, label, element=guid)
                nodes[split_key] = _Node(
                    split_key, split_kind, gate, label, element=guid
                )
                entry[guid], exit_[guid] = join_key, split_key
            else:
                kind = "join" if n_in >= 2 else split_kind
                nodes[guid] = _Node(guid, kind, gate, label, element=guid)
                entry[guid] = exit_[guid] = guid
        else:  # event
            if n_in == 0 or n_out == 0:
                kind = vocab.by_kind("start" if n_in == 0 else "end").kind
                nodes[guid] = _Node(guid, str(kind), None, label, element=guid)
                entry[guid] = exit_[guid] = guid
    for guid, role in epc.control.items():
        if role == "event" and guid not in nodes:
            after_split = any(p in split_rules for p in epc.pred[guid])
            folded[guid] = "condition" if after_split else "state"

    flows: set[tuple[str, str, str | None, bool]] = set()
    pending: list[tuple[str, str, list[str]]] = []
    for guid in sorted(epc.control):
        if guid in folded:
            continue
        for target in epc.succ[guid]:
            stack: list[tuple[str, list[str]]] = [(target, [])]
            while stack:
                cur, chain = stack.pop()
                if cur in folded:
                    if cur in chain:
                        continue
                    for nxt in reversed(epc.succ[cur]):
                        stack.append((nxt, [*chain, cur]))
                    continue
                cond = next(
                    (
                        normalize_text(epc.objects[e].get("name"))
                        for e in chain
                        if folded[e] == "condition"
                    ),
                    None,
                )
                flows.add((exit_[guid], entry[cur], cond, False))
                pending.append((exit_[guid], entry[cur], chain))
    for key, node in nodes.items():
        if key.endswith("#join"):
            flows.add((key, f"{node.element}#split", None, False))

    index = number_steps(nodes, [(s, t) for s, t, _c, _d in flows])
    seen_events: set[str] = set()
    for after, before, chain in sorted(
        pending, key=lambda p: (index[p[0]], index[p[1]], p[2])
    ):
        for event in chain:
            if event in seen_events:
                continue
            seen_events.add(event)
            annex.append(
                {
                    "after": after,
                    "before": before,
                    "construct": f"epc-{folded[event]}-event",
                    "element_id": event,
                    "label": normalize_text(epc.objects[event].get("name")) or "",
                }
            )
    annex.sort(
        key=lambda a: (
            index.get(a["after"], 0),
            index.get(a.get("before", ""), 0),
            a["construct"] != "epc-attachment",
        )
    )
    return build_canonical(
        str(model.get("name") or ""),
        nodes,
        flows,
        system=SYSTEM,
        model_id=_rid(model),
        annex=annex,
    )


def aml_model_to_canonical(bundle: AmlModel) -> dict[str, Any]:
    """The canonical workflow of one model read from AML."""
    return epc_to_canonical(bundle.model, bundle.objects, bundle.connections)


# ── canonical -> EPC ───────────────────────────────────────────────────────


def validate_canonical(doc: Any) -> dict[str, Any]:
    """Refuse ``PROCESS_CANONICAL_INVALID`` unless ``doc`` is a v1 canonical."""

    def bad(message: str) -> CanonicalError:
        return CanonicalError("PROCESS_CANONICAL_INVALID", message)

    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except json.JSONDecodeError as exc:
            raise bad(f"canonical workflow is not JSON: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise bad(f"schema must be {SCHEMA!r}")
    steps, flows = doc.get("steps"), doc.get("flows")
    if not isinstance(steps, list) or not isinstance(flows, list):
        raise bad("steps and flows must be lists")
    ids = set()
    for step in steps:
        if not isinstance(step, dict) or not step.get("id"):
            raise bad("every step needs an id")
        if step.get("kind") not in CANONICAL_KINDS:
            raise bad(f"step {step['id']}: kind {step.get('kind')!r} is not canonical")
        if step.get("gate") is not None and step["gate"] not in GATES:
            raise bad(f"step {step['id']}: gate {step['gate']!r} is not canonical")
        ids.add(step["id"])
    for flow in flows:
        if not isinstance(flow, dict) or {flow.get("source"), flow.get("target")} - ids:
            raise bad(f"flow {flow!r} names an unknown step")
    if doc.get("digest") and doc["digest"] != compute_digest(steps, flows):
        raise bad("digest does not match the steps and flows")
    return doc


def _guid_for(model_guid: str, *parts: str) -> str:
    return str(uuid.uuid5(_NS, "/".join([model_guid, *parts])))


def _cxn_type(source_type: str, target_type: str) -> str:
    if source_type == "OT_EVT":
        return "CT_ACTIV_1" if target_type == "OT_FUNC" else "CT_LNK_2"
    if source_type == "OT_FUNC":
        return "CT_CRT_1" if target_type == "OT_EVT" else "CT_LEADS_TO_1"
    return "CT_LNK_2" if target_type == "OT_FUNC" else "CT_LNK_3"


def _loss(element: str | None, construct: str, treatment: str) -> dict[str, Any]:
    return {
        "element": element,
        "construct": construct,
        "target": "epc",
        "treatment": treatment,
    }


class _EpcBuilder:
    def __init__(self, model_guid: str) -> None:
        self.model_guid = model_guid
        self.objects: dict[str, dict[str, Any]] = {}
        self.connections: list[dict[str, Any]] = []

    def obj(self, guid: str, name: str, type_num: str, symbol: str) -> str:
        if guid not in self.objects:
            self.objects[guid] = {
                "guid": guid,
                "id": "ObjDef." + "".join(c if c.isalnum() else "_" for c in guid),
                "name": name,
                "type": type_num,
                "symbol": symbol,
                "attributes": {"AT_NAME": name} if name else {},
            }
        return guid

    def link(self, source: str, target: str, ctype: str | None = None) -> None:
        guid = _guid_for(self.model_guid, "cxn", source, target)
        if any(c["guid"] == guid for c in self.connections):
            return
        ctype = ctype or _cxn_type(
            self.objects[source]["type"], self.objects[target]["type"]
        )
        self.connections.append(
            {
                "guid": guid,
                "id": "CxnDef." + guid.replace("-", "_"),
                "type": ctype,
                "sourceObjectId": source,
                "targetObjectId": target,
            }
        )


def canonical_to_epc(doc: Any, *, strict: bool = False) -> dict[str, Any]:
    """EPC records (model, objects, connections) of a canonical workflow.

    Returns ``{"model", "objects", "connections", "losses"}``. With ``strict``
    a lossy export refuses ``PROCESS_EXPORT_LOSSY`` listing the losses.
    """
    doc = validate_canonical(doc)
    vocab = vocabulary()
    source = doc.get("source") or {}
    same_source = source.get("system") == SYSTEM
    elements: dict[str, str] = dict(source.get("elements") or {}) if same_source else {}
    digest = doc.get("digest") or compute_digest(doc["steps"], doc["flows"])
    model_guid = str(source.get("model_id") or "") if same_source else ""
    model_guid = model_guid or str(uuid.uuid5(_NS, digest))
    annex = list(doc.get("annex") or [])
    steps = {s["id"]: s for s in doc["steps"]}
    losses: list[dict[str, Any]] = []
    epc = _EpcBuilder(model_guid)

    for entry in annex:
        if not str(entry.get("construct", "")).startswith("epc-"):
            losses.append(
                _loss(
                    entry.get("after") or entry.get("element_id"),
                    str(entry.get("construct")),
                    "kept only in the source format; EPC has no equivalent",
                )
            )

    out_flows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for flow in doc["flows"]:
        out_flows[flow["source"]].append(flow)

    # a join directly followed by a split from the same source gate is one operator
    merged: dict[str, str] = {}
    for sid, step in steps.items():
        nxt = out_flows.get(sid, [])
        if step["kind"] == "join" and len(nxt) == 1:
            target = steps[nxt[0]["target"]]
            if (
                target["kind"] in ("branch", "fork")
                and target.get("gate") == step.get("gate")
                and elements.get(sid)
                and elements.get(sid) == elements.get(target["id"])
            ):
                merged[target["id"]] = sid

    obj_of: dict[str, str] = {}
    it_support = vocab.attachment_by_role("it-support").type_nums[0]
    performer_type = vocab.attachment_by_role("performer").type_nums[0]
    rule_type = vocab.attachment_by_role("decision-rule").type_nums[0]
    event_type = vocab.by_kind("start").type_nums[0]
    function_type = vocab.by_kind("agent").type_nums[0]
    interface_symbol = vocab.by_kind("call").symbol_nums[0]

    for sid, step in steps.items():
        if sid in merged:
            continue
        guid = elements.get(sid) or _guid_for(model_guid, "step", sid)
        label = step.get("label") or ""
        kind, ref, role = step["kind"], step.get("ref"), step.get("role")
        if kind in ("start", "end"):
            obj_of[sid] = epc.obj(guid, label, event_type, "ST_EV")
        elif kind in _FUNCTION_KINDS:
            symbol = interface_symbol if kind == "call" else "ST_FUNC"
            obj_of[sid] = epc.obj(guid, label, function_type, symbol)
            if role:
                org = epc.obj(
                    _guid_for(model_guid, "performer", role),
                    role,
                    performer_type,
                    "ST_ORG_UNIT_2",
                )
                epc.link(org, guid, "CT_EXEC_1")
            if kind == "agent" and role:
                it = epc.obj(
                    _guid_for(model_guid, "it-support"),
                    "Automated agent",
                    it_support,
                    "ST_APPL_SYS_TYPE",
                )
                epc.link(it, guid, "CT_CAN_SUPP_1")
            if kind == "human" and not role:
                losses.append(
                    _loss(
                        sid,
                        "unassigned-human-step",
                        "exported as a function with no performer; it reads back as an automated step",
                    )
                )
            if kind == "decision":
                rule = epc.obj(
                    _guid_for(model_guid, "rule", ref or label),
                    ref or label,
                    rule_type,
                    "ST_BUSINESS_RULE",
                )
                epc.link(rule, guid, "CT_IS_ASSIGN_1")
                if not same_source:
                    losses.append(
                        _loss(
                            sid,
                            "decision-table",
                            f"function plus business rule {ref or label!r}; the decision table stays in the engine",
                        )
                    )
        elif kind in _GATE_KINDS or (kind == "wait" and step.get("gate")):
            gate = step.get("gate") or ("xor" if kind == "branch" else "and")
            cls = vocab.by_gate(gate)
            obj_of[sid] = epc.obj(guid, label, cls.type_nums[0], cls.symbol_nums[0])
            if kind == "wait":
                losses.append(
                    _loss(
                        sid,
                        "event-based-gateway",
                        "exported as an XOR split followed by the events",
                    )
                )
        else:  # wait, boundary
            name = f"{label} ({ref})" if ref else label
            obj_of[sid] = epc.obj(guid, name, event_type, "ST_EV")
            losses.append(
                _loss(
                    sid,
                    "typed-trigger" if kind == "wait" else "boundary-event",
                    "exported as an event named with its trigger"
                    if kind == "wait"
                    else "exported as an event on the path; interrupt semantics lost",
                )
            )
    for split, join in merged.items():
        obj_of[split] = obj_of[join]

    for entry in annex:
        if entry.get("construct") == "epc-attachment" and entry.get("after") in obj_of:
            att = epc.obj(
                str(entry["element_id"]),
                str(entry.get("label") or ""),
                str(entry.get("type_num") or "OT_UNKNOWN"),
                "",
            )
            epc.link(att, obj_of[entry["after"]], "CT_IS_ASSIGN_1")

    restored: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in annex:
        if entry.get("construct") == "epc-state-event":
            restored[(entry.get("after"), entry.get("before"))].append(entry)
    conditions = {
        (e.get("after"), e.get("before"), e.get("label")): e
        for e in annex
        if e.get("construct") == "epc-condition-event"
    }

    def event(guid: str, name: str) -> str:
        return epc.obj(guid, name, event_type, "ST_EV")

    for flow in sorted(doc["flows"], key=lambda f: (f["source"], f["target"])):
        u, v = flow["source"], flow["target"]
        if merged.get(v) == u:
            continue
        chain: list[str] = []
        su, sv = steps[u], steps[v]
        cond = flow.get("condition")
        if flow.get("default"):
            losses.append(
                _loss(u, "default-flow", "exported as an 'otherwise' condition event")
            )
            cond = cond or "otherwise"
        if cond and not (sv["kind"] in _EVENT_KINDS and sv.get("label") == cond):
            known = conditions.get((u, v, cond))
            guid = (
                str(known["element_id"])
                if known
                else _guid_for(model_guid, "condition", u, v)
            )
            chain.append(event(guid, cond))
        for entry in restored.get((u, v), []):
            chain.append(event(str(entry["element_id"]), str(entry.get("label") or "")))
        if (
            not chain
            and su["kind"] in _FUNCTION_KINDS
            and sv["kind"] in _FUNCTION_KINDS
        ):
            chain.append(
                event(
                    _guid_for(model_guid, "state", u, v),
                    f"{su.get('label') or ''} completed".strip(),
                )
            )
        path = [obj_of[u], *chain, obj_of[v]]
        for a, b in zip(path, path[1:], strict=False):
            epc.link(a, b)

    name = doc.get("name") or ""
    if strict and losses:
        raise CanonicalError(
            "PROCESS_EXPORT_LOSSY",
            f"{len(losses)} construct(s) cannot be expressed in EPC",
            losses,
        )
    model = {
        "guid": model_guid,
        "id": "Model." + "".join(c if c.isalnum() else "_" for c in model_guid),
        "name": name,
        "type": vocab.classes["EpcModel"].type_nums[0],
        "groupPath": "Main group",
        "attributes": {"AT_NAME": name} if name else {},
    }
    return {
        "model": model,
        "objects": list(epc.objects.values()),
        "connections": epc.connections,
        "losses": losses,
    }


# ── leaf-class typing (used by the KG ingest) ──────────────────────────────

_KIND_CLASS = {
    "human": "EpcHumanFunction",
    "agent": "EpcAutomatedFunction",
    "decision": "EpcDecisionFunction",
    "call": "EpcProcessInterface",
}


def _typed_by_hint(obj: dict[str, Any], vocab: EpcVocabulary) -> dict[str, Any]:
    """``obj`` with a TypeNum (and rule symbol) guessed from its type name.

    Used only when a record carries no ARIS TypeNum the ontology knows, for
    tenants whose REST layer returns type names instead of constants.
    """
    type_num = str(obj.get("type") or "")
    known = vocab.control_type_nums | {
        t for c in vocab.classes.values() if c.attachment_role for t in c.type_nums
    }
    if type_num in known:
        return obj
    hint = " ".join(
        str(obj.get(k) or "")
        for k in ("type", "typeName", "symbol", "symbolName", "objectType")
    ).lower()
    if not hint.strip():
        return obj
    guessed = dict(obj)
    if "event" in hint:
        guessed["type"] = vocab.by_kind("start").type_nums[0]
    elif any(h in hint for h in ("rule", "operator", "connector", "xor")):
        words = set(re.findall(r"[a-z]+", hint))
        gate = "and" if "and" in words else "or" if "or" in words else "xor"
        cls = vocab.by_gate(gate)
        guessed["type"], guessed["symbol"] = cls.type_nums[0], cls.symbol_nums[0]
    elif "func" in hint or "task" in hint or "activity" in hint:
        guessed["type"] = vocab.by_kind("agent").type_nums[0]
    return guessed


def classify_epc_objects(
    objects: list[dict[str, Any]], connections: list[dict[str, Any]]
) -> dict[str, str]:
    """The leaf ontology class of every object: TypeNum/SymbolNum first, the
    type-name hints only as a fallback."""
    vocab = vocabulary()
    typed = [_typed_by_hint(o, vocab) for o in objects]
    epc = _load(typed, connections)
    out: dict[str, str] = {}
    for guid, obj in epc.objects.items():
        role = epc.control.get(guid)
        if role == "function":
            out[guid] = _KIND_CLASS[_function_node(epc, guid, []).kind]
        elif role == "event":
            if not epc.pred[guid]:
                out[guid] = "EpcStartEvent"
            elif not epc.succ[guid]:
                out[guid] = "EpcEndEvent"
            else:
                out[guid] = "EpcIntermediateEvent"
        elif role == "rule":
            cls = vocab.gate_for_symbol(str(obj.get("symbol") or ""))
            out[guid] = cls.name if cls else "EpcXorOperator"
        else:
            cls = vocab.attachment_class(str(obj.get("type") or ""))
            out[guid] = cls.name if cls else "EpcAttachment"
    return out
