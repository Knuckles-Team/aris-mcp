"""The EPC vocabulary as declared in ``ontology/aris.ttl``.

The EPC <-> canonical workflow mapping is read from the ontology annotations
(``:arisTypeNum``, ``:arisSymbolNum``, ``:dagNodeKind``, ``:canonicalGateKind``,
``:epcAttachmentRole``), so the ontology is the one source of truth. The file is
parsed with a small reader of the subset of Turtle the file uses: one
``:Name a owl:Class ; ... .`` block per class.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

_BLOCK = re.compile(r"^:(\w+) a owl:Class\b(.*?)\s\.\s*$", re.M | re.S)
_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')

CANONICAL_KINDS = frozenset(
    {
        "start",
        "end",
        "human",
        "agent",
        "decision",
        "branch",
        "fork",
        "join",
        "wait",
        "call",
        "boundary",
    }
)
SOURCE_ONLY_KINDS = frozenset({"graph", "state"})
GATES = frozenset({"and", "or", "xor"})


@dataclass(frozen=True)
class EpcClass:
    """One class of the EPC ontology with its mapping annotations."""

    name: str
    parents: tuple[str, ...]
    type_nums: tuple[str, ...] = ()
    symbol_nums: tuple[str, ...] = ()
    kind: str | None = None
    gate: str | None = None
    attachment_role: str | None = None
    tools: tuple[str, ...] = ()


def _values(body: str, prop: str) -> tuple[str, ...]:
    match = re.search(rf"{re.escape(prop)}\s+(.+?)\s*(?:;|$)", body, re.S)
    return tuple(_STRING.findall(match.group(1))) if match else ()


def _parents(body: str) -> tuple[str, ...]:
    match = re.search(r"rdfs:subClassOf ([^;]+?)\s*(?:;|$)", body, re.S)
    return tuple(re.findall(r":(\w+)", match.group(1))) if match else ()


def ontology_text() -> str:
    """The packaged ``aris.ttl``."""
    return (
        resources.files("aris_mcp")
        .joinpath("ontology", "aris.ttl")
        .read_text(encoding="utf-8")
    )


def parse_classes(text: str) -> dict[str, EpcClass]:
    """Every ``owl:Class`` block of ``text`` by local name."""
    classes: dict[str, EpcClass] = {}
    for match in _BLOCK.finditer(text):
        name, body = match.group(1), match.group(2)
        kinds = _values(body, ":dagNodeKind")
        gates = _values(body, ":canonicalGateKind")
        roles = _values(body, ":epcAttachmentRole")
        classes[name] = EpcClass(
            name=name,
            parents=_parents(body),
            type_nums=_values(body, ":arisTypeNum"),
            symbol_nums=_values(body, ":arisSymbolNum"),
            kind=kinds[0] if kinds else None,
            gate=gates[0] if gates else None,
            attachment_role=roles[0] if roles else None,
            tools=_values(body, ":executedByTool"),
        )
    return classes


@dataclass(frozen=True)
class EpcVocabulary:
    """The lookups the adapters need, derived from the ontology classes."""

    classes: dict[str, EpcClass]

    def by_kind(self, kind: str) -> EpcClass:
        """The one class whose ``:dagNodeKind`` is ``kind`` and that has a type."""
        found = [c for c in self.classes.values() if c.kind == kind and c.type_nums]
        if kind in ("fork", "branch"):
            raise KeyError(f"{kind} is a gate kind; use by_gate")
        if len(found) != 1:
            raise KeyError(f"no single EPC class has dagNodeKind {kind!r}")
        return found[0]

    def by_gate(self, gate: str) -> EpcClass:
        """The rule-operator class whose ``:canonicalGateKind`` is ``gate``."""
        for cls in self.classes.values():
            if cls.gate == gate:
                return cls
        raise KeyError(gate)

    @property
    def function_type_nums(self) -> frozenset[str]:
        kinds = {"human", "agent", "decision", "call"}
        return frozenset(
            t for c in self.classes.values() if c.kind in kinds for t in c.type_nums
        )

    @property
    def event_type_nums(self) -> frozenset[str]:
        kinds = {"start", "end", "state"}
        return frozenset(
            t for c in self.classes.values() if c.kind in kinds for t in c.type_nums
        )

    @property
    def rule_type_nums(self) -> frozenset[str]:
        return frozenset(
            t for c in self.classes.values() if c.gate for t in c.type_nums
        )

    @property
    def control_type_nums(self) -> frozenset[str]:
        return self.function_type_nums | self.event_type_nums | self.rule_type_nums

    def interface_symbols(self) -> frozenset[str]:
        return frozenset(self.by_kind("call").symbol_nums)

    def gate_for_symbol(self, symbol: str | None) -> EpcClass | None:
        for cls in self.classes.values():
            if cls.gate and symbol in cls.symbol_nums:
                return cls
        return None

    def attachment_class(self, type_num: str | None) -> EpcClass | None:
        """The attachment class covering ``type_num``, or ``None`` when unknown."""
        for cls in self.classes.values():
            if cls.attachment_role and type_num in cls.type_nums:
                return cls
        return None

    def attachment_by_role(self, role: str) -> EpcClass:
        for cls in self.classes.values():
            if cls.attachment_role == role:
                return cls
        raise KeyError(role)


@cache
def vocabulary() -> EpcVocabulary:
    """The vocabulary of the packaged ontology (parsed once)."""
    return EpcVocabulary(parse_classes(ontology_text()))
