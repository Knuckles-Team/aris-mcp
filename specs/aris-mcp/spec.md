# CONN-ARIS-MCP — Process source, AML and the canonical workflow

**Owner:** this repository.

See [`requirements.md`](requirements.md) for the definition of every requirement ID this spec owns.

## Outcome

The business's process models reach the platform from ARIS whether or not an ARIS tenant exists: the connector serves a live tenant, a directory of AML exports, or a bundled fixture repository, and refuses with a typed reason when nothing is configured. Every EPC model converts to the one canonical workflow the engine builds agent workflow graphs from, with the same digest as the BPMN version of the same process, and a canonical workflow converts back to EPC with every loss stated.

## Why a new spec

The specs of this repository were read (`git grep -n "canonical\|AML\|source mode" -- specs`): `CONN-ARIS-MCP-CONNECTOR-CONTENT` owns packaged content and `CONN-ARIS-MCP-SDK-CENTRALIZATION` owns the governed transport. Neither owns source resolution, AML or the EPC to canonical adapter, so this spec states them for this connector.

## Scope and interfaces

In scope: the rows of [requirements.md](requirements.md). Out of scope: the canonical workflow store, the native BPMN reader and the agent workflow graph (owned by the engine), and the shared transport (owned by the SDK).

## User Scenarios & Testing

### User Story 1 - Process models without an ARIS tenant (Priority: P1)

An operator with no ARIS instance still connects ARIS-authored processes: the connector serves AML exports or the fixture repository, and says exactly what to configure when nothing is set.

**Acceptance Scenarios**:

1. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R001` (source resolution, typed refusals and health) is exercised, **Then** `tests/test_source.py::test_unconfigured_refuses_typed` passes.
2. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R002` (aml reader) is exercised, **Then** `tests/test_aml.py::test_reader_refuses_doctype_and_entities` passes.
3. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R003` (aml writer) is exercised, **Then** `tests/test_aml.py::test_writer_round_trips_through_the_reader` passes.
4. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R006` (fixture repository) is exercised, **Then** `tests/test_source.py::test_fixture_repository_serves_the_samples_through_read_tools` passes.
5. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R007` (one typed tool per operation) is exercised, **Then** `tests/test_tool_surface.py::test_surface_is_one_typed_tool_per_operation` passes.

### User Story 2 - One canonical workflow for EPC and BPMN (Priority: P1)

A process modeler converts an EPC to the canonical workflow and back, and the same process authored as BPMN yields the same digest and agent workflow graph.

**Acceptance Scenarios**:

1. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R004` (epc to canonical workflow) is exercised, **Then** `tests/test_canonical.py::test_epc_to_canonical_equals_the_golden` passes.
2. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R005` (canonical workflow to epc with loss rules) is exercised, **Then** `tests/test_canonical.py::test_same_source_round_trip_keeps_digest_and_annex` passes.
3. **Given** the connector is served, **When** the behaviour of row `CONN-ARIS-MCP-R008` (cross-source equivalence fixture) is exercised, **Then** `tests/test_equivalence.py::test_epc_and_bpmn_give_the_same_digest_and_dag` passes.

### Edge Cases

- If `CONN-ARIS-MCP-R001` is not met, its proving test fails: source resolution, typed refusals and health.
- If `CONN-ARIS-MCP-R002` is not met, its proving test fails: aml reader.
- If `CONN-ARIS-MCP-R003` is not met, its proving test fails: aml writer.
- If `CONN-ARIS-MCP-R004` is not met, its proving test fails: epc to canonical workflow.
- If `CONN-ARIS-MCP-R005` is not met, its proving test fails: canonical workflow to epc with loss rules.
- If `CONN-ARIS-MCP-R006` is not met, its proving test fails: fixture repository.
- If `CONN-ARIS-MCP-R007` is not met, its proving test fails: one typed tool per operation.
- If `CONN-ARIS-MCP-R008` is not met, its proving test fails: cross-source equivalence fixture.
- A DOCTYPE or entity in an AML export is refused before parsing.
- A canonical workflow with a timer, boundary event or default flow cannot be exported strictly.

## Requirements

- **FR-001**: Source resolution, typed refusals and health. Rows: `CONN-ARIS-MCP-R001`.
- **FR-002**: AML reader. Rows: `CONN-ARIS-MCP-R002`.
- **FR-003**: AML writer. Rows: `CONN-ARIS-MCP-R003`.
- **FR-004**: EPC to canonical workflow. Rows: `CONN-ARIS-MCP-R004`.
- **FR-005**: Canonical workflow to EPC with loss rules. Rows: `CONN-ARIS-MCP-R005`.
- **FR-006**: Fixture repository. Rows: `CONN-ARIS-MCP-R006`.
- **FR-007**: One typed tool per operation. Rows: `CONN-ARIS-MCP-R007`.
- **FR-008**: Cross-source equivalence fixture. Rows: `CONN-ARIS-MCP-R008`.

## Success Criteria

- **SC-001**: `tests/test_source.py::test_unconfigured_refuses_typed`. Rows: `CONN-ARIS-MCP-R001`.
- **SC-002**: `tests/test_aml.py::test_reader_refuses_doctype_and_entities`. Rows: `CONN-ARIS-MCP-R002`.
- **SC-003**: `tests/test_aml.py::test_writer_round_trips_through_the_reader`. Rows: `CONN-ARIS-MCP-R003`.
- **SC-004**: `tests/test_canonical.py::test_epc_to_canonical_equals_the_golden`. Rows: `CONN-ARIS-MCP-R004`.
- **SC-005**: `tests/test_canonical.py::test_same_source_round_trip_keeps_digest_and_annex`. Rows: `CONN-ARIS-MCP-R005`.
- **SC-006**: `tests/test_source.py::test_fixture_repository_serves_the_samples_through_read_tools`. Rows: `CONN-ARIS-MCP-R006`.
- **SC-007**: `tests/test_tool_surface.py::test_surface_is_one_typed_tool_per_operation`. Rows: `CONN-ARIS-MCP-R007`.
- **SC-008**: `tests/test_equivalence.py::test_epc_and_bpmn_give_the_same_digest_and_dag`. Rows: `CONN-ARIS-MCP-R008`.

## Assumptions

- AML exports follow the ARIS Markup Language structure (groups, object and connection definitions, models with occurrences).
- The canonical workflow contract (`medulla.process.canonical/v1`) is the engine's; this connector produces and consumes it.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-ARIS-MCP-R001` | [plan.md](plan.md) | T-001 | [test-spec.md](test-spec.md) |
| FR-002 | `CONN-ARIS-MCP-R002` | [plan.md](plan.md) | T-002 | [test-spec.md](test-spec.md) |
| FR-003 | `CONN-ARIS-MCP-R003` | [plan.md](plan.md) | T-003 | [test-spec.md](test-spec.md) |
| FR-004 | `CONN-ARIS-MCP-R004` | [plan.md](plan.md) | T-004 | [test-spec.md](test-spec.md) |
| FR-005 | `CONN-ARIS-MCP-R005` | [plan.md](plan.md) | T-005 | [test-spec.md](test-spec.md) |
| FR-006 | `CONN-ARIS-MCP-R006` | [plan.md](plan.md) | T-006 | [test-spec.md](test-spec.md) |
| FR-007 | `CONN-ARIS-MCP-R007` | [plan.md](plan.md) | T-007 | [test-spec.md](test-spec.md) |
| FR-008 | `CONN-ARIS-MCP-R008` | [plan.md](plan.md) | T-008 | [test-spec.md](test-spec.md) |
