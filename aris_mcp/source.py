"""Where the ARIS repository comes from, and the typed refusals of every tool.

Resolution, first match wins:

* ``live`` - ``ARIS_API_BASE`` is set: the REST client of :mod:`aris_mcp.auth`.
* ``fixture`` - ``ARIS_REPOSITORY_DIR=fixture``: the bundled sample repository
  under ``aris_mcp/fixtures/repository/`` (every response is tagged
  ``"repository": "fixture"``).
* ``files`` - ``ARIS_REPOSITORY_DIR`` names a directory of AML exports, served
  read-only.
* ``unconfigured`` - neither is set. Every repository tool refuses
  ``ARIS_NOT_CONFIGURED``; the server still starts and ``/health`` answers.

Refusals travel as a fastmcp ``ToolError`` whose message is a JSON object
``{"code", "message", "remedy"}`` (plus ``details`` when there are any).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from fastmcp.exceptions import ToolError
from scion_sdk.config import setting
from scion_sdk.utilities import to_boolean

from aris_mcp.aml import AmlError, AmlModel, read_aml

logger = logging.getLogger("aris_mcp.source")

LIVE, FILES, FIXTURE, UNCONFIGURED = "live", "files", "fixture", "unconfigured"
FIXTURE_VALUE = "fixture"
AML_SUFFIXES = (".aml", ".xml")


class ArisRefusal(ToolError):
    """A typed refusal: a stable code, what happened, and how to fix it."""

    def __init__(
        self, code: str, message: str, remedy: str = "", details: Any = None
    ) -> None:
        self.code, self.message, self.remedy, self.details = (
            code,
            message,
            remedy,
            details,
        )
        body: dict[str, Any] = {"code": code, "message": message, "remedy": remedy}
        if details is not None:
            body["details"] = details
        super().__init__(json.dumps(body, ensure_ascii=False))


def not_configured() -> ArisRefusal:
    return ArisRefusal(
        "ARIS_NOT_CONFIGURED",
        "No ARIS repository is configured for this connector.",
        "Set ARIS_API_BASE (and one auth path) for a live tenant, or "
        "ARIS_REPOSITORY_DIR to a directory of AML exports (ARIS_REPOSITORY_DIR="
        "fixture serves the bundled sample repository).",
    )


def read_only(mode: str) -> ArisRefusal:
    return ArisRefusal(
        "ARIS_READ_ONLY_SOURCE",
        f"The {mode} repository is read-only.",
        "Writes reach only a live tenant: set ARIS_API_BASE and ARIS_ENABLE_WRITE=true.",
    )


def write_disabled() -> ArisRefusal:
    return ArisRefusal(
        "ARIS_WRITE_DISABLED",
        "ARIS writes are disabled.",
        "Set ARIS_ENABLE_WRITE=true to allow attribute writes on the live tenant.",
    )


def model_not_found(model_id: str) -> ArisRefusal:
    return ArisRefusal(
        "ARIS_MODEL_NOT_FOUND",
        f"No model {model_id!r} in the repository.",
        "List the models with aris_list_models and pass one of their guid values.",
    )


def writes_enabled() -> bool:
    return to_boolean(os.getenv("ARIS_ENABLE_WRITE", "False"))


@dataclass(frozen=True)
class SourceConfig:
    """The resolved source mode and where its repository is."""

    mode: str
    location: str | None = None


def resolve_mode() -> SourceConfig:
    """The source mode from the environment (no I/O beyond a directory check)."""
    base = (setting("ARIS_API_BASE", "") or "").strip()
    if base:
        return SourceConfig(LIVE, base)
    repo = (setting("ARIS_REPOSITORY_DIR", "") or "").strip()
    if repo == FIXTURE_VALUE:
        return SourceConfig(FIXTURE, str(fixture_dir()))
    if repo:
        return SourceConfig(FILES, repo)
    return SourceConfig(UNCONFIGURED)


def fixture_dir() -> Path:
    return Path(str(resources.files("aris_mcp").joinpath("fixtures", "repository")))


class FileRepository:
    """A read-only repository served from a directory of AML exports.

    It answers the read methods of the live client with the same record shapes.
    """

    def __init__(self, directory: Path, label: str) -> None:
        self.directory = directory
        self.label = label
        self.bundles: dict[str, AmlModel] = {}
        if not directory.is_dir():
            raise ArisRefusal(
                "ARIS_REPOSITORY_MISSING",
                f"ARIS_REPOSITORY_DIR {str(directory)!r} is not a directory.",
                "Point ARIS_REPOSITORY_DIR at a directory of AML exports.",
            )
        for path in sorted(directory.rglob("*")):
            if path.suffix.lower() not in AML_SUFFIXES or not path.is_file():
                continue
            try:
                models = read_aml(path.read_bytes())
            except AmlError as exc:
                logger.warning("skipping %s: %s", path.name, exc)
                continue
            for bundle in models:
                self.bundles[str(bundle.model["guid"])] = bundle

    def _bundle(self, model_id: str) -> AmlModel:
        bundle = self.bundles.get(str(model_id))
        if bundle is None:
            for candidate in self.bundles.values():
                if candidate.model.get("id") == model_id:
                    return candidate
            raise model_not_found(model_id)
        return bundle

    def list_models(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        models = [dict(b.model) for b in self.bundles.values()]
        name = (params or {}).get("name")
        if name:
            models = [m for m in models if str(name).lower() in m["name"].lower()]
        offset = int((params or {}).get("offset") or 0)
        limit = (params or {}).get("limit")
        models = models[offset:]
        return models[: int(limit)] if limit else models

    def get_model(self, model_id: str) -> dict[str, Any]:
        return dict(self._bundle(model_id).model)

    def list_model_objects(self, model_id: str) -> list[dict[str, Any]]:
        return [dict(o) for o in self._bundle(model_id).objects]

    def list_model_connections(self, model_id: str) -> list[dict[str, Any]]:
        return [dict(c) for c in self._bundle(model_id).connections]

    def list_model_attributes(self, model_id: str) -> dict[str, Any]:
        model = self._bundle(model_id).model
        return {"modelId": model["guid"], "attributes": dict(model["attributes"])}

    def set_model_attributes(self, model_id: str, attributes: dict[str, Any]) -> Any:
        raise read_only(self.label)

    def set_object_attributes(self, object_id: str, attributes: dict[str, Any]) -> Any:
        raise read_only(self.label)


@cache
def _file_repository(directory: str, label: str) -> FileRepository:
    return FileRepository(Path(directory), label)


def get_source() -> tuple[str, Any]:
    """``(mode, repository)`` for the current environment, or the typed refusal."""
    config = resolve_mode()
    if config.mode == LIVE:
        from aris_mcp.auth import get_client

        return LIVE, get_client()
    if config.mode in (FILES, FIXTURE):
        return config.mode, _file_repository(str(config.location), config.mode)
    raise not_configured()


def source_status() -> dict[str, Any]:
    """Mode, repository location, model count and whether writes are enabled."""
    config = resolve_mode()
    status: dict[str, Any] = {
        "mode": config.mode,
        "repository": config.location,
        "model_count": None,
        "writes_enabled": config.mode == LIVE and writes_enabled(),
    }
    if config.mode in (FILES, FIXTURE):
        try:
            status["model_count"] = len(
                _file_repository(str(config.location), config.mode).bundles
            )
        except ArisRefusal as exc:
            status["error"] = {"code": exc.code, "message": exc.message}
    elif config.mode == UNCONFIGURED:
        status["remedy"] = not_configured().remedy
    return status


def log_resolved_mode(*_args: Any) -> None:
    """Log the resolved source once when the server is built."""
    config = resolve_mode()
    # the startup line is shown at the default WARNING root level too
    logger.setLevel(min(logger.getEffectiveLevel(), logging.INFO))
    logger.info(
        "aris-mcp source mode: %s%s",
        config.mode,
        f" ({config.location})" if config.mode in (FILES, FIXTURE) else "",
    )
