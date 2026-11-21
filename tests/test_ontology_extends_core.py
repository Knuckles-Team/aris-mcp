"""CONN-ARIS-MCP-CONNECTOR-CONTENT-R007: the pack extends only the core ontology."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.spec("CONN-ARIS-MCP-CONNECTOR-CONTENT-R007")

PACKAGE = Path(__file__).resolve().parents[1] / "aris_mcp"


def test_attachment_roots_under_the_core_domain_entity() -> None:
    text = (PACKAGE / "ontology" / "aris.ttl").read_text()
    block = re.search(r"^:EpcAttachment a owl:Class ;\n(.*?)\n\n", text, re.M | re.S)
    assert block is not None
    assert "rdfs:subClassOf core:DomainEntity" in block.group(1)
    assert "core:Concept" not in block.group(1)
    sources = (PACKAGE / "connector_sources.py").read_text()
    assert '"EpcAttachment": "DomainEntity"' in sources
