"""Keep the ARIS development skill bound to the connector contract."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "aris_mcp" / "skills" / "aris-mcp-development" / "SKILL.md"


@pytest.mark.spec("PIPE-CONNSPEC-R104.4")
def test_aris_development_skill_describes_the_supported_delivery_contract():
    text = SKILL.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pipeline = (ROOT / ".github/workflows/pipeline.yml").read_text(encoding="utf-8")
    pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert SKILL.is_file()
    assert re.search(r"^name:\s*aris-mcp-development\s*$", frontmatter, re.M)
    assert re.search(r"^skill_type:\s*skill\s*$", frontmatter, re.M)
    assert "## Rapid delivery: the 5-minute contract" in text
    for term in (
        "aris_mcp/__init__.py",
        "aris_mcp/api/api_client_aris.py",
        "aris_mcp/auth.py",
        "aris_mcp/mcp/mcp_aris.py",
        "aris_mcp/connector_sources.py",
        "ARIS_API_BASE",
        "ARIS_OAUTH_URL",
        "ARIS_CLIENT_ID",
        "ARIS_CLIENT_SECRET",
        "ARIS_TENANT",
        "ARIS_TOKEN",
        "ARIS_USERNAME",
        "ARIS_PASSWORD",
        "ARIS_TLS_PROFILE",
        "ARIS_TLS_PROFILE_REF",
        "ARIS_PATHS_JSON",
        "ARIS_ENABLE_WRITE",
        "aris_model",
        "aris_object",
        "aris_ingest_models",
        "aris_ingest_model_export",
        "agent_connector_sdk.cli:serve",
        "aris_mcp/skills/**",
        "connector: true",
        "render_connector: true",
        "pages_pipeline.yml@main",
        "uv run --locked --extra test pytest",
    ):
        assert term in text

    assert "verify=False" not in text
    assert "--no-verify" not in text
    assert '"skills/**"' in pyproject
    assert "python_pipeline.yml@main" in pipeline
    assert "connector: true" in pipeline
    assert "container_pipeline.yml@main" in pipeline
    assert "render_connector: true" in pipeline
    assert "pages_pipeline.yml@main" in pages
