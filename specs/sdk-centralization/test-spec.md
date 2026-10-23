# CONN-ARIS-MCP-SDK-CENTRALIZATION — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Level | Setup and input | Expected observation | Evidence |
|---|---|---|---|---|---|
| T-001 | `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001` | Unit | Every child row. | See each child. |  |
| T-002 | `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.1` | Unit | `tests/test_sdk_transport.py::test_client_is_governed_and_sends_bearer_auth` | The session is an SDK client with bearer auth and the package imports no `requests`. |  |
| T-003 | `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.2` | Unit | `tests/test_auth.py::test_oauth_token_fetch_uses_resolved_tls_profile` | The token client is built with the resolved profile. |  |
| T-004 | `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.3` | Unit | `tests/test_sdk_transport.py::test_request_shapes_are_unchanged` | A request sends its JSON body and an error status raises as before. |  |
| T-005 | `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.4` | Unit | `tests/test_sdk_transport.py::test_dependencies_come_from_the_sdk` | `pyproject.toml` has no `requests` pin and the SDK floor is `0.3.11` or later. |  |
