# CONN-ARIS-MCP-CONNECTOR-CONTENT — The connector serves its packaged content

Owner: aris-mcp. Cross-repo IDs: `SCION-CONNECTOR-CONTROL-R071`, `SCION-CONNECTOR-CONTROL-R073`.

## Purpose and user stories

The `aris-mcp` server serves its packaged skills, prompts and ontology to any client, with no wiring of its own.

## Why a new spec

The specs of this repository were read; none owns this capability. This spec states it for this connector only.

## Scope and interfaces

In scope: the rows of [requirements.md](requirements.md). Out of scope: the SDK modules and the engine, which own the shared capabilities.

## User Scenarios & Testing

### User Story 1 - The connector serves its packaged content (Priority: P1)

The `aris-mcp` server serves its packaged skills, prompts and ontology to any client, with no wiring of its own.

**Acceptance Scenarios**:

1. **Given** the connector is configured, **When** the behaviour of row `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001` (default content) is exercised, **Then** `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. Planned test: `tests/test_default_content_surfaces.py::test_default_content_lists_skill_and_ontology_resources_and_prompts`.
2. **Given** the connector is configured, **When** the behaviour of row `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002` (declare access contracts for the competency reads of aris-mcp) is exercised, **Then** declare access contracts for the competency reads of aris-mcp.

### User Story 2 - EPC and the canonical workflow share one vocabulary (Priority: P1)

An agent that reads or converts ARIS EPC models finds the EPC classes, their canonical step kinds, the tools, the skills, the agent prompts and the tool-use contracts in the connector's content.

**Acceptance Scenarios**:

1. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003` (epc ontology maps epc to the canonical workflow and rolls up to core) is exercised, **Then** `tests/test_ontology.py::test_every_class_reaches_a_core_class` passes.
2. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004` (skills name only served tools and write up the proven workflows) is exercised, **Then** `tests/test_surface_contracts.py::test_skills_name_only_served_tools_and_link_to_tasks` passes.
3. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005` (prompts are complete agent definitions) is exercised, **Then** `tests/test_surface_contracts.py::test_prompts_are_complete_agent_definitions` passes.
4. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006` (tool-use contracts, links, data locations and roles) is exercised, **Then** `tests/test_surface_contracts.py::test_every_tool_is_called_by_a_contract_and_named_by_a_link` passes.

### Edge Cases

- If `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001` is not met, its proving test fails: default content.
- If `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002` is not met, its proving test fails: declare access contracts for the competency reads of aris-mcp.
- If `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003` is not met, its proving test fails: epc ontology maps epc to the canonical workflow and rolls up to core.
- If `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004` is not met, its proving test fails: skills name only served tools and write up the proven workflows.
- If `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005` is not met, its proving test fails: prompts are complete agent definitions.
- If `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006` is not met, its proving test fails: tool-use contracts, links, data locations and roles.

## Requirements

- **FR-003**: EPC ontology maps EPC to the canonical workflow and rolls up to core. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003`.
- **FR-004**: Skills name only served tools and write up the proven workflows. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004`.
- **FR-005**: Prompts are complete agent definitions. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005`.
- **FR-006**: Tool-use contracts, links, data locations and roles. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006`.
- **FR-001**: Default content. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001`.
- **FR-002**: Declare access contracts for the competency reads of aris-mcp. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002`.

## Success Criteria

- **SC-003**: `tests/test_ontology.py::test_every_class_reaches_a_core_class`. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003`.
- **SC-004**: `tests/test_surface_contracts.py::test_skills_name_only_served_tools_and_link_to_tasks`. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004`.
- **SC-005**: `tests/test_surface_contracts.py::test_prompts_are_complete_agent_definitions`. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005`.
- **SC-006**: `tests/test_surface_contracts.py::test_every_tool_is_called_by_a_contract_and_named_by_a_link`. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006`.

- **SC-001**: `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. Planned test: `tests/test_default_content_surfaces.py::test_default_content_lists_skill_and_ontology_resources_and_prompts`. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001`.
- **SC-002**: Declare access contracts for the competency reads of aris-mcp. Rows: `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002`.

## Assumptions

- The external system is reachable with operator-supplied credentials.
- The SDK and engine contracts the rows cite are at the floors declared in `pyproject.toml`.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R001` | [plan.md](plan.md) | T-001 | [test-spec.md](test-spec.md) |
| FR-002 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R002` | [plan.md](plan.md) | T-002 | [test-spec.md](test-spec.md) |
| FR-003 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R003` | [plan.md](plan.md) | T-003 | [test-spec.md](test-spec.md) |
| FR-004 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R004` | [plan.md](plan.md) | T-004 | [test-spec.md](test-spec.md) |
| FR-005 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R005` | [plan.md](plan.md) | T-005 | [test-spec.md](test-spec.md) |
| FR-006 | `CONN-ARIS-MCP-CONNECTOR-CONTENT-R006` | [plan.md](plan.md) | T-006 | [test-spec.md](test-spec.md) |
