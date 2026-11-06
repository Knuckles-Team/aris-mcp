# CONN-ARIS-MCP — Quickstart

The shortest path that shows the served behaviour working.

- `CONN-ARIS-MCP-R001`, `CONN-ARIS-MCP-R006`: run `pytest tests/test_source.py`; start the server with `ARIS_REPOSITORY_DIR=fixture` and call `aris_get_source_status` and `aris_list_models`.
- `CONN-ARIS-MCP-R002`, `CONN-ARIS-MCP-R003`: run `pytest tests/test_aml.py`.
- `CONN-ARIS-MCP-R004`, `CONN-ARIS-MCP-R005`: run `pytest tests/test_canonical.py tests/test_conversion_tools.py`; call `aris_export_canonical_workflow` with the text of `tests/fixtures/invoice-approval.aml`.
- `CONN-ARIS-MCP-R007`: run `pytest tests/test_tool_surface.py`.
- `CONN-ARIS-MCP-R008`: run `pytest tests/test_equivalence.py`.
