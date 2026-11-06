"""CONN-ARIS-MCP-R002, R003: the AML reader and writer."""

from pathlib import Path

import pytest

from aris_mcp.aml import MAX_AML_BYTES, AmlError, read_aml, write_aml

FIXTURE = Path(__file__).parent / "fixtures" / "invoice-approval.aml"


@pytest.mark.spec("CONN-ARIS-MCP-R002")
def test_reader_returns_live_client_record_shapes():
    [bundle] = read_aml(FIXTURE.read_bytes())
    model = bundle.model
    assert set(model) == {"guid", "id", "name", "type", "groupPath", "attributes"}
    assert model["name"] == "Invoice approval"
    assert model["type"] == "MT_EEPC"
    assert model["groupPath"] == "Main group/Finance"
    assert all(
        set(o) == {"guid", "id", "name", "type", "symbol", "attributes"}
        for o in bundle.objects
    )
    names = {o["name"]: o for o in bundle.objects}
    # AT_NAME as plain AttrValue text and as StyledElement/PlainText
    assert names["Check invoice"]["type"] == "OT_FUNC"
    assert names["Invoice received"]["symbol"] == "ST_EV"
    assert len(bundle.objects) == 24
    assert len(bundle.connections) == 28
    guids = {o["guid"] for o in bundle.objects}
    for cxn in bundle.connections:
        assert set(cxn) == {"guid", "id", "type", "sourceObjectId", "targetObjectId"}
        assert {cxn["sourceObjectId"], cxn["targetObjectId"]} <= guids


@pytest.mark.spec("CONN-ARIS-MCP-R002")
@pytest.mark.parametrize(
    "document",
    [
        '<?xml version="1.0"?><!DOCTYPE AML [<!ENTITY x "boom">]><AML>&x;</AML>',
        '<?xml version="1.0"?><!DOCTYPE AML SYSTEM "file:///etc/passwd"><AML/>',
        '<?xml version="1.0"?><!DOCTYPE AML><AML/>',
    ],
)
def test_reader_refuses_doctype_and_entities(document):
    with pytest.raises(AmlError, match="refused"):
        read_aml(document)


@pytest.mark.spec("CONN-ARIS-MCP-R002")
def test_reader_refuses_oversize_malformed_and_foreign_documents():
    with pytest.raises(AmlError, match="exceeds"):
        read_aml(b"<AML>" + b" " * MAX_AML_BYTES + b"</AML>")
    with pytest.raises(AmlError, match="well-formed"):
        read_aml("<AML><Group></AML>")
    with pytest.raises(AmlError, match="not an AML document"):
        read_aml("<definitions/>")


@pytest.mark.spec("CONN-ARIS-MCP-R003")
def test_writer_round_trips_through_the_reader():
    models = read_aml(FIXTURE.read_bytes())
    text = write_aml(models)
    assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<AML>')
    again = read_aml(text)
    assert [(m.model, m.objects, m.connections) for m in again] == [
        (m.model, m.objects, m.connections) for m in models
    ]
    assert write_aml(again) == text
