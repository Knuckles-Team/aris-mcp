"""Shared pytest configuration for aris-mcp."""


def pytest_configure(config):
    """Register the spec marker that binds a test to a requirement row."""
    config.addinivalue_line(
        "markers", "spec(id): Binds a test to a requirement row of a spec."
    )
