# CONN-ARIS-MCP-SDK-CENTRALIZATION — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A child row `.n` is one five-minute unit of work. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001` | **Capabilities come from the SDK (rollup).** The connector must use the SDK for HTTP, retry, TLS and optional dependencies. Children `.1` to `.4` deliver it. | See each child. |
| `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.1` | **Governed client.** The API client and the OAuth token request must send HTTP through the SDK governed client and must not import `requests` (`SCION-CENTRALIZED-CAPABILITIES-R001`, `SCION-CENTRALIZED-CAPABILITIES-R003`). Bearer and basic credentials must travel as client auth, not as default headers. Proving test: `tests/test_sdk_transport.py::test_client_is_governed_and_sends_bearer_auth`. | The session is an SDK client with bearer auth and the package imports no `requests`. |
| `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.2` | **TLS profile only.** Every connection, including the OAuth token request, must take its trust from the `resolve_tls_profile` result for the `aris` prefix (`SCION-CENTRALIZED-CAPABILITIES-R008`). The connector must not read a verification flag. Proving test: `tests/test_auth.py::test_oauth_token_fetch_uses_resolved_tls_profile`. | The token client is built with the resolved profile. |
| `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.3` | **Same behaviour.** Each API method must keep its path, body and result shape. A status of 400 or more must raise `API error: <status> - <text>`. Proving test: `tests/test_sdk_transport.py::test_request_shapes_are_unchanged`. | A request sends its JSON body and an error status raises as before. |
| `CONN-ARIS-MCP-SDK-CENTRALIZATION-R001.4` | **SDK floor.** The package must depend on `agent-connector-sdk[mcp]` at the latest release floor and must not pin `requests` (`SCION-CENTRALIZED-CAPABILITIES-R040`). Proving test: `tests/test_sdk_transport.py::test_dependencies_come_from_the_sdk`. | `pyproject.toml` has no `requests` pin and the SDK floor is `0.3.11` or later. |
