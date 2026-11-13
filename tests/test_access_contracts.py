"""CONN-ARIS-MCP-CONNECTOR-CONTENT-R002: the competency reads are declared as
access contracts and each recorded response satisfies its contract."""

import asyncio
import json
from pathlib import Path

import pytest
from fastmcp import Client
from scion_sdk.access_contract import parse_access_contracts
from scion_sdk.connector import build_server

from aris_mcp.vocabulary import ontology_text

ID = "CONN-ARIS-MCP-CONNECTOR-CONTENT-R002"
ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = parse_access_contracts(
    (ROOT / "aris_mcp/ontology/access_contracts.ttl").read_text()
)
ONTOLOGY = ontology_text()
CONNECTOR_NS = "https://knuckles-team.github.io/ontology/connector/aris#"
MODEL = "5e0c0a11-0000-4000-8000-000000000001"


def _tools():
    async def names():
        _, mcp = build_server("aris_mcp", command_args=[])
        async with Client(mcp) as client:
            return {t.name for t in await client.list_tools()}

    return asyncio.run(names())


@pytest.mark.spec(ID)
def test_competency_contracts_certified(monkeypatch):
    monkeypatch.delenv("ARIS_API_BASE", raising=False)
    monkeypatch.setenv("ARIS_REPOSITORY_DIR", "fixture")
    assert {c.entity for c in CONTRACTS} == {"epc_function", "connection"}
    tools = _tools()
    for contract in CONTRACTS:
        assert contract.source_id == "aris-mcp"
        assert contract.access_kind == "mcp_tool"
        assert contract.operation in tools
        assert contract.pagination == "none"
        assert contract.key_field == "id"
        for prop, _field in contract.predicates:
            if prop.startswith(CONNECTOR_NS):
                local = prop.removeprefix(CONNECTOR_NS)
                assert f"\n:{local} a owl:" in ONTOLOGY, local
            assert prop.rsplit("#", 1)[1] in {"modelId", "name", "sourceId", "targetId"}
        recording = json.loads(
            (ROOT / f"tests/recordings/{contract.entity}.json").read_text()
        )
        records = recording[contract.records_path]
        assert records
        for record in records:
            assert contract.key_field in record
            assert all(field in record for _, field in contract.predicates)

        async def served(contract=contract):
            _, mcp = build_server("aris_mcp", command_args=[])
            async with Client(mcp) as client:
                result = await client.call_tool(contract.operation, {"model_id": MODEL})
                return result.structured_content

        live = asyncio.run(served())
        assert all(r in live[contract.records_path] for r in records)


@pytest.mark.spec(ID)
def test_contract_refuses_a_recording_missing_a_bound_field():
    (contract,) = [c for c in CONTRACTS if c.entity == "connection"]
    record = {"id": "x", "sourceObjectId": "a"}
    assert not all(field in record for _, field in contract.predicates)
