# CONN-ARIS-MCP — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-ARIS-MCP-R001` | `tests/test_source.py::test_unconfigured_refuses_typed` | Source resolution, typed refusals and health. |
| T-002 | `CONN-ARIS-MCP-R002` | `tests/test_aml.py::test_reader_refuses_doctype_and_entities` | AML reader. |
| T-003 | `CONN-ARIS-MCP-R003` | `tests/test_aml.py::test_writer_round_trips_through_the_reader` | AML writer. |
| T-004 | `CONN-ARIS-MCP-R004` | `tests/test_canonical.py::test_epc_to_canonical_equals_the_golden` | EPC to canonical workflow. |
| T-005 | `CONN-ARIS-MCP-R005` | `tests/test_canonical.py::test_same_source_round_trip_keeps_digest_and_annex` | Canonical workflow to EPC with loss rules. |
| T-006 | `CONN-ARIS-MCP-R006` | `tests/test_source.py::test_fixture_repository_serves_the_samples_through_read_tools` | Fixture repository. |
| T-007 | `CONN-ARIS-MCP-R007` | `tests/test_tool_surface.py::test_surface_is_one_typed_tool_per_operation` | One typed tool per operation. |
| T-008 | `CONN-ARIS-MCP-R008` | `tests/test_equivalence.py::test_epc_and_bpmn_give_the_same_digest_and_dag` | Cross-source equivalence fixture. |

Further proofs: `tests/test_source.py` (R001, R006), `tests/test_aml.py` (R002, R003), `tests/test_canonical.py` and `tests/test_conversion_tools.py` (R004, R005), `tests/test_tool_surface.py` (R007), `tests/test_equivalence.py` (R008).
