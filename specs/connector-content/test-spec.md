# CONN-ARIS-MCP-CONNECTOR-CONTENT — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001` | `tests/test_default_content_surfaces.py` | The listings include the packaged skills, ontology and prompts. |
| T-003 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003` | `tests/test_ontology.py::test_every_class_reaches_a_core_class` | EPC ontology maps EPC to the canonical workflow and rolls up to core. |
| T-004 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004` | `tests/test_surface_contracts.py::test_skills_name_only_served_tools_and_link_to_tasks` | Skills name only served tools and write up the proven workflows. |
| T-005 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005` | `tests/test_surface_contracts.py::test_prompts_are_complete_agent_definitions` | Prompts are complete agent definitions. |
| T-006 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006` | `tests/test_surface_contracts.py::test_every_tool_is_called_by_a_contract_and_named_by_a_link` | Tool-use contracts, links, data locations and roles. |

## Rows awaiting bound tests
- `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002`: proof `tests/test_access_contracts.py::test_competency_contracts_certified`; the test carries the row's `spec` marker when it lands.
