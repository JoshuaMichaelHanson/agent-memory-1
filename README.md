# agent-memory

`agent-memory` is a small Python CLI for durable AI-agent memory backed by SQLite.

The first release is a command-line tool. The code is intentionally structured so a future MCP adapter can call the same service layer rather than shelling out to the CLI or duplicating database logic.

## Current Status

This branch has completed Phase 5 from `docs/BACKLOG.md`: packaging, module entry points, configuration, SQLite schema initialization, `init`, `status`, `put`, `get`, `recent`, and `search`.

The `init`, `status`, `put`, `get`, `recent`, and `search` commands are implemented. Delete, mirror, and export commands remain placeholders until later phases.

## Quick Start During Development

Create a project-local virtual environment and install the package in editable mode with development dependencies:

```powershell
.\scripts\setup-dev.ps1
```

After setup, use either the activated console script:

```powershell
.\.venv\Scripts\Activate.ps1
agent-memory --help
pytest
```

or call the venv Python directly:

```powershell
.\.venv\Scripts\python.exe -m agent_memory --help
.\.venv\Scripts\python.exe -m pytest
```

POSIX shells:

```sh
./scripts/setup-dev.sh
. ./.venv/bin/activate
agent-memory --help
pytest
```

See `docs/DEVELOPMENT_ENVIRONMENT.md` for the project policy on Python versions, virtual environments, and CLI installation.

## Planned Commands

- `init`
- `status`
- `put`
- `get`
- `search`
- `recent`
- `delete`
- `mirror-file`
- `export-md`

## Design Notes

- Python 3.11+.
- Runtime dependencies should stay within the Python standard library for version 1.
- SQLite is the canonical memory store.
- Markdown files are bootstrap context or generated exports, not the source of truth once the database works.
- Current user instructions and repository files override stored memory.
- Do not store secrets, credentials, tokens, private keys, or protected personal data.

## Development

The project uses standard Python packaging through `pyproject.toml`:

- `requires-python = ">=3.11"` declares compatible Python versions.
- Runtime dependencies are intentionally empty for version 1.
- Development dependencies live in the `dev` optional dependency group.
- `requirements-dev.txt` is a convenience wrapper around `-e .[dev]`.

Run tests inside the venv:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The smoke tests can also run without pytest:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```
