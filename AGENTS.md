# aris-mcp - AGENTS

> Claude Code loads this file via `CLAUDE.md` (`@AGENTS.md` import) — the two stay
> in sync. Edit **this** file, not `CLAUDE.md`.

## Project Structure
- `aris_mcp/`: server code (`api/` REST client, `mcp/` thin tools, `auth.py`, `mcp_server.py`, `agent_server.py`)
- `tests/`: test suite
- `mcp_config.json`: connection template

## Tech Stack
- Python 3.11+
- agent-utilities >= 0.49.0
- requests (ARIS REST API, OAuth2/bearer/basic)
- Model Context Protocol (MCP) via FastMCP

## Commands
- `pytest`: run tests
- `pre-commit run --all-files`: lint

## Design notes
- The client is a **thin** REST wrapper; all logic stays in the agent-utilities KG
  extractor/writeback. Method names (`list_models`, `list_model_objects`,
  `list_model_connections`, `set_model_attributes`) are the contract the KG
  extractor probes — keep them stable.
- Endpoint **paths are configurable** (`ARIS_PATHS_JSON`) because ARIS tenants
  differ; only the paths move, never the method names.
- Writes are gated by `ARIS_ENABLE_WRITE` (default off).

## Quality Bar
Run `pre-commit run --all-files` and drive it fully green before committing. Do
not silence checks to force green. Never commit secrets.

<!-- BEGIN concept-coordination (generated) -->
## Concept-ID Coordination (multi-session)

Working in parallel with other sessions/worktrees? **Reserve a concept id before you write its `CONCEPT:` marker** so two sessions never collide:

```bash
agent-utilities --json concept reserve --ns KG-2   # or a package prefix, e.g. KEY
```

Full protocol (ledger, merge=union, reconcile, MCP/REST): <https://knuckles-team.github.io/agent-utilities/concept_coordination/>
<!-- END concept-coordination (generated) -->

## Version & lockfile drift edict (keep the version mirrors AND the lock in sync)

The two most common release-breakers in this fleet are **version drift** (the version in
`pyproject.toml`/`.bumpversion.cfg` advancing while `README.md`, `docker/Dockerfile`, and the
module `__version__`s lag) and a **stale `uv.lock`** (shipping known-vulnerable transitive deps).
A version mismatch makes the next `bump-my-version` throw `VersionNotFoundException`; a stale lock
is what Dependabot flags. Rules:

1. **Never hand-edit a version string.** Change the version ONLY via
   `bump-my-version bump {patch|minor|major}` (a.k.a. `bump2version`), which rewrites every file
   registered in `.bumpversion.cfg` in one atomic, tagged commit. If you edited the version in
   `pyproject.toml` by hand, you created drift — revert and use the bumper.
2. **Every version-bearing file must be registered in `.bumpversion.cfg`** — at minimum
   `pyproject.toml` AND `README.md`, plus `docker/Dockerfile` and any module `__version__`. Never
   add a file that embeds the version without a `[bumpversion:file:...]` entry for it.
3. **Re-lock on every dependency change.** After editing `pyproject.toml` deps/extras, run
   `uv lock` and commit `uv.lock` in the SAME change. The `uv-lock` pre-commit hook runs with
   `--locked` and fails on drift — never bypass it. The committed `uv.lock` is the
   Dependabot/security surface.
4. **Patch CVEs with a version floor at the source, then re-lock.** `uv` resolves one version
   graph-wide, so a lower-bound in the extra that pulls a dependency raises it for the whole lock.
