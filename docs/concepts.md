# ARIS Concept Registry

## Concepts

### ARIS-001: Core API Client Operations
- **Description**: Granular `requests`-based REST client (`ArisApi`) with coverage of the ARIS API — model inventory, per-model EPC objects, control-flow connections, and attribute read/write.
- **Traceability**: `aris_mcp/api/`

### ARIS-002: FastMCP Tools Execution
- **Description**: FastMCP tools, one typed tool per operation, over a resolved source (live tenant, AML directory or bundled fixture repository), plus EPC <-> canonical workflow conversion.
- **Traceability**: `aris_mcp/mcp/`

### ARIS-003: Identity & Gateway Security
- **Description**: Secure credential loading (OAuth2 client-credentials, static bearer, HTTP basic), tenant path overrides, and SSL verification settings.
- **Traceability**: `aris_mcp/auth.py`
