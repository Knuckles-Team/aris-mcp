"""Surface-contract declaration types and their Turtle rendering.

The shapes match the connector surface standard (``connector-surface``): a
tool-use contract names a task and its ordered tool steps, a link joins prompts,
skills and tools to a task, a data location says which instance holds which
classes, and a business role names the tasks one role performs. The rendered
Turtle types individuals with the surface-contract vocabulary, whose classes
extend core classes; nothing here imports the core ontology.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field

CONTRACT_NS = "https://knuckles-team.github.io/ontology/surface-contract#"
CORE_NS = "https://knuckles-team.github.io/ontology/core#"
CONNECTOR_NS = "https://knuckles-team.github.io/ontology/connector/aris#"


@dataclass(frozen=True)
class Refusal:
    """One refusal a step can return: its code and the condition."""

    code: str
    when: str = ""


@dataclass(frozen=True)
class ToolStep:
    """One ordered tool call of a task."""

    tool: str
    params: tuple[str, ...] = ()
    result: tuple[str, ...] = ()
    refusals: tuple[Refusal, ...] = ()


@dataclass(frozen=True)
class ToolUseContract:
    """Which tools a task uses, in what order."""

    task: str
    steps: tuple[ToolStep, ...]
    description: str = ""


@dataclass(frozen=True)
class SurfaceLink:
    """Prompts, skills and tools joined to the task they serve."""

    task: str
    tools: tuple[str, ...] = ()
    prompts: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataLocation:
    """Which instance or store holds which classes, and the tool that reads them."""

    name: str
    holds: tuple[str, ...]
    instance: str
    read_tool: str
    store: str = ""
    route_param: str = ""
    federation_key: str = ""


@dataclass(frozen=True)
class BusinessRole:
    """One business role the connector serves, and the tasks it performs."""

    name: str
    tasks: tuple[str, ...] = ()
    description: str = ""


@dataclass
class _Turtle:
    connector: str
    lines: list[str] = field(default_factory=list)
    written: set[str] = field(default_factory=set)

    def iri(self, kind: str, name: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in name)
        return f"<urn:connector:{self.connector}:{kind}:{safe}>"

    def refusal(self, refusal: Refusal) -> str:
        """The shared node of one refusal shape, written once."""
        digest = hashlib.sha256(f"{refusal.code}|{refusal.when}".encode()).hexdigest()
        iri = self.iri("refusal", f"{refusal.code}-{digest[:12]}")
        if iri not in self.written:
            self.written.add(iri)
            self.node(
                iri,
                "sc:Refusal",
                [
                    ("sc:refusalCode", _literal(refusal.code)),
                    ("sc:refusalWhen", _literal(refusal.when)),
                ],
            )
        return iri

    def node(self, subject: str, types: str, pairs: Iterable[tuple[str, str]]) -> None:
        body = [f"{subject} a {types}"] + [f"    {p} {o}" for p, o in pairs]
        self.lines.append(" ;\n".join(body) + " .\n")


def _literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def _contract(out: _Turtle, contract: ToolUseContract) -> None:
    task = out.iri("task", contract.task)
    out.node(task, "kg:Task", [("rdfs:label", _literal(contract.task))])
    step_iris = []
    for order, step in enumerate(contract.steps, start=1):
        step_iri = out.iri("step", f"{contract.task}.{order}")
        step_iris.append(step_iri)
        pairs = [
            ("sc:stepOrder", str(order)),
            ("sc:callsTool", out.iri("tool", step.tool)),
        ]
        pairs += [("sc:param", _literal(p)) for p in step.params]
        pairs += [("sc:resultField", _literal(r)) for r in step.result]
        for refusal in step.refusals:
            pairs.append(("sc:refusal", out.refusal(refusal)))
        out.node(step_iri, "sc:ToolStep", pairs)
    for before, after in zip(step_iris, step_iris[1:], strict=False):
        out.lines.append(f"{before} kg:precedes {after} .\n")
    pairs = [("sc:forTask", task)] + [("kg:hasPart", s) for s in step_iris]
    if contract.description:
        pairs.append(("rdfs:comment", _literal(contract.description)))
    out.node(out.iri("contract", contract.task), "sc:ToolUseContract", pairs)


def _link(out: _Turtle, link: SurfaceLink) -> None:
    task = out.iri("task", link.task)
    for kind, names, cls in (
        ("prompt", link.prompts, "kg:Prompt"),
        ("skill", link.skills, "kg:Skill"),
    ):
        for name in names:
            pairs = [("sc:servesTask", task)]
            pairs += [("sc:usesTool", out.iri("tool", t)) for t in link.tools]
            out.node(out.iri(kind, name), cls, pairs)
    for tool in link.tools:
        out.node(out.iri("tool", tool), "kg:Tool", [("sc:servesTask", task)])


def _location(out: _Turtle, location: DataLocation) -> None:
    pairs = [("sc:holdsClass", f"kg:{cls}") for cls in location.holds]
    pairs += [
        ("sc:instance", _literal(location.instance)),
        ("sc:readTool", out.iri("tool", location.read_tool)),
    ]
    for prop, value in (
        ("sc:store", location.store),
        ("sc:routeParam", location.route_param),
        ("sc:federationKey", location.federation_key),
    ):
        if value:
            pairs.append((prop, _literal(value)))
    out.node(out.iri("location", location.name), "sc:DataLocation", pairs)


def _role(out: _Turtle, role: BusinessRole) -> None:
    pairs = [("rdfs:label", _literal(role.name))]
    pairs += [("sc:servesTask", out.iri("task", t)) for t in role.tasks]
    if role.description:
        pairs.append(("rdfs:comment", _literal(role.description)))
    out.node(out.iri("role", role.name), "sc:BusinessRole", pairs)


def render_surface_turtle(
    connector: str,
    contracts: Iterable[ToolUseContract],
    links: Iterable[SurfaceLink],
    locations: Iterable[DataLocation],
    roles: Iterable[BusinessRole],
    prompts: dict[str, dict[str, object]] | None = None,
) -> str:
    """The declarations as Turtle individuals of the surface-contract vocabulary.

    ``prompts`` maps each prompt name to its ``agent`` object, so each prompt
    also records its agent kind, business role, skills and data locations.
    """
    out = _Turtle(connector)
    out.lines += [
        f"@prefix sc: <{CONTRACT_NS}> .\n",
        f"@prefix kg: <{CORE_NS}> .\n",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n",
        "\n",
    ]
    for contract in contracts:
        _contract(out, contract)
    for link in links:
        _link(out, link)
    for location in locations:
        _location(out, location)
    for role in roles:
        _role(out, role)
    for name, agent in (prompts or {}).items():
        pairs = [("sc:agentKind", _literal(str(agent.get("kind", ""))))]
        if agent.get("business_role"):
            pairs.append(
                ("sc:businessRole", out.iri("role", str(agent["business_role"])))
            )
        pairs += [
            ("sc:usesSkill", out.iri("skill", str(s)))
            for s in agent.get("skills", ())  # type: ignore[union-attr]
        ]
        data = agent.get("data") or {}
        pairs += [
            ("sc:readsLocation", out.iri("location", str(n)))
            for n in data.get("reads", ())  # type: ignore[union-attr]
        ]
        pairs += [
            ("sc:writesLocation", out.iri("location", str(n)))
            for n in data.get("writes", ())  # type: ignore[union-attr]
        ]
        out.node(out.iri("prompt", name), "kg:Prompt", pairs)
    return "".join(out.lines)
