# CONN-ARIS-MCP-CONNECTOR-CONTENT — Quickstart

The shortest path that shows the served behaviour working.

- `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003`: run `pytest tests/test_ontology.py tests/test_kg_ingest.py`; read `ontology://aris-mcp/aris.ttl` from the running server.
- `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004`: run `pytest tests/test_surface_contracts.py -k skills`; read `skill://aris-epc-to-canonical-workflow/SKILL.md`.
- `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005`: run `pytest tests/test_surface_contracts.py -k prompts`; get the prompt `aris-process-modeler`.
- `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006`: run `pytest tests/test_surface_contracts.py`; read `ontology://aris-mcp/contracts.ttl`.
