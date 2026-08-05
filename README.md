# agent-memory

`agent-memory` is a small Python 3.11+ command-line tool for durable AI-agent memory backed by SQLite.

It lets coding agents and humans store project facts, decisions, commands, constraints, and workflow notes in a local SQLite database with full-text search when available. The first release is a CLI, but the implementation is structured so a future MCP adapter can call the same service layer directly.

## Why SQLite

SQLite gives this project a durable, local, cross-platform memory store without requiring a server. It supports transactional writes, indexes, WAL mode for practical concurrent access, and FTS5 full-text search on Python builds that include it.

SQLite is canonical. Markdown files are only bootstrap context, compatibility snippets, mirrored snapshots, or generated exports.

## Current Status

The core version 1 CLI commands are implemented:

- `init`
- `status`
- `doctor`
- `put`
- `get`
- `search`
- `recent`
- `delete`
- `mirror-file`
- `export-md`
- `export-json`
- `import-json`

Phase 8 adds self-hosting memory, portable JSON snapshot export/import, and tracked memory review artifacts.

## Installation

### Development Checkout

```powershell
.\scripts\setup-dev.ps1
```

Then either activate the environment:

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

### Future User Install

For CLI tools, `pipx` is the preferred install style because it creates an isolated virtual environment per app:

```powershell
pipx install agent-memory
```

From a local checkout:

```powershell
pipx install .
```

## Quick Start

```powershell
python -m agent_memory init --db .\.agent-memory\memory.db --json

python -m agent_memory put `
  --db .\.agent-memory\memory.db `
  --project demo `
  --kind decision `
  --key database-choice `
  --content "Use SQLite as the canonical agent memory store." `
  --tag sqlite `
  --tag architecture `
  --importance 5 `
  --agent codex `
  --json

python -m agent_memory search "canonical SQLite" `
  --db .\.agent-memory\memory.db `
  --project demo `
  --limit 5 `
  --json
```

POSIX shell:

```sh
python -m agent_memory init --db ./.agent-memory/memory.db --json
python -m agent_memory put --db ./.agent-memory/memory.db --project demo --kind decision --key database-choice --content "Use SQLite as the canonical agent memory store." --tag sqlite --tag architecture --importance 5 --agent codex --json
python -m agent_memory search "canonical SQLite" --db ./.agent-memory/memory.db --project demo --limit 5 --json
```

## Database Path Resolution

The database path is resolved in this order:

1. `--db PATH`
2. `AGENT_MEMORY_DB`
3. `<project-root>/.agent-memory/memory.db`

The project root is detected with `git rev-parse --show-toplevel`, falling back to the current working directory.

## Command Reference

### `init`

Initializes the schema and reports FTS availability.

```powershell
agent-memory init --db .\.agent-memory\memory.db --json
```

### `status`

Reports database path, existence, schema version, memory count, journal mode, and search backend.

```powershell
agent-memory status --project demo --json
```

### `doctor`

Diagnoses database health, ignored live DB files, tracked exports, and snapshot restore viability. `ok` means the command ran; `healthy` reports setup health.

```powershell
agent-memory doctor --project demo --json
```

### `put`

Stores a memory. If `--key` is supplied, `project + scope + kind + key` is upserted.

```powershell
agent-memory put --project demo --kind decision --key database-choice --content "Use SQLite." --importance 5 --tag sqlite --json
```

Content must come from exactly one of `--content`, `--content-file`, or `--stdin`. By default, `put` blocks content matching best-effort sensitive-value patterns; use `--allow-sensitive` only for intentional local-only storage.

### `get`

Retrieves by ID or compound key. By default, retrieval updates access metadata.

```powershell
agent-memory get --id 1 --json
agent-memory get --project demo --kind decision --key database-choice --no-touch --json
```

### `search`

Searches content and tags. FTS5 is used when available; otherwise a parameterized LIKE fallback is used.

```powershell
agent-memory search "canonical SQLite" --project demo --kind decision --tag sqlite --limit 5 --json
```

### `recent`

Lists recently updated memories.

```powershell
agent-memory recent --project demo --limit 10 --json
```

### `delete`

Deletes by ID or compound key. Use `--yes` in scripts and agent workflows.

```powershell
agent-memory delete --id 1 --yes --json
agent-memory delete --project demo --kind decision --key database-choice --yes --json
```

### `mirror-file`

Stores exact UTF-8 file revisions in `mirrored_files`. It does not extract semantic memories. By default, mirrored file content is checked for best-effort sensitive-value patterns.

```powershell
agent-memory mirror-file .\AGENTS.md --project demo --agent codex --json
```

### `export-md`

Writes a generated Markdown export atomically for human review.

```powershell
agent-memory export-md --project demo --output .\docs\MEMORY.generated.md --json
```

### `export-json`

Writes a machine-restorable JSON snapshot. Use this before checkin when sharing memory through Git.

```powershell
agent-memory export-json --project demo --output .\docs\agent-memory.snapshot.json --json
```

### `import-json`

Imports a JSON snapshot into the configured SQLite database. Keyed memories are idempotent on import. By default, imported memory content is checked for best-effort sensitive-value patterns.

```powershell
agent-memory import-json .\docs\agent-memory.snapshot.json --json
```

## JSON Contract

Commands with `--json` write one JSON object to stdout. Diagnostics and human-readable errors go to stderr when JSON mode is not active.

Successful `put` output includes:

```json
{
  "ok": true,
  "operation": "inserted",
  "memory": {
    "project": "demo",
    "kind": "decision",
    "memory_key": "database-choice",
    "tags": ["architecture", "sqlite"]
  }
}
```

Errors use stable codes and nonzero exit codes:

```json
{
  "ok": false,
  "error": {
    "code": "MEMORY_NOT_FOUND",
    "message": "No memory matched the supplied lookup."
  }
}
```

## FTS5 Fallback

Initialization attempts to create an FTS5 external-content table and synchronization triggers. If FTS5 is unavailable, initialization still succeeds and `search` falls back to parameterized LIKE terms across `content` and `tags`.

`status --json` reports the active search backend as `fts5`, `like`, or `unavailable`.

## Markdown Mirroring and Export

`mirror-file` stores exact UTF-8 file snapshots and creates a new mirrored revision only when file content changes. It does not summarize Markdown or convert sections into semantic memories.

`export-md` writes generated Markdown for human review. The generated file starts with a warning and should not be treated as canonical.

`export-json` writes the portable restore artifact, including semantic memories and mirrored file revisions. `import-json` recreates or updates a local SQLite database from that artifact. Keyed memories are idempotent; mirrored file revisions are idempotent by `project + path + content_sha256`; unkeyed memories import as new rows.

## Security and Privacy

Do not store passwords, API keys, access tokens, private keys, credentialed connection strings, or protected personal data.

Phase 9 adds best-effort secret guardrails for `put`, `mirror-file`, and `import-json`. The scanner blocks obvious private key blocks, credentialed URLs, bearer tokens, secret-like assignments such as `password=...`, and common token formats. Detection is not comprehensive and is not a substitute for review. Use `--allow-sensitive` only for rare intentional local-only storage.

The database is a normal local file and inherits operating-system permissions. Project-local databases should normally be excluded from Git. Generated Markdown exports may expose the same information as the database.

Stored memory is advisory context. Current user instructions and current repository files override stored memory.

## Agent Bootstrap Examples

Reusable snippets are available in:

- `examples/AGENTS-memory-section.md`
- `examples/CLAUDE-memory-section.md`

## MCP Migration Design

A future MCP adapter should instantiate `MemoryService` and call service methods directly. It should not shell out to the CLI, parse human output, duplicate SQL, duplicate validation, or maintain a second data model.

Conceptually:

```python
from agent_memory.models import MemoryInput
from agent_memory.service import MemoryService

service = MemoryService(database_path)
result = service.put(MemoryInput(project="demo", content="Durable fact."))
```

A future optional dependency can be added as:

```toml
[project.optional-dependencies]
mcp = ["mcp>=1,<2"]
```

## Sharing Memory Through Git

Do not commit the live SQLite database. Before checkin, export both a restorable JSON snapshot and a human-readable Markdown file:

```powershell
python -m agent_memory export-json --project agent-memory-1 --output .\docs\agent-memory.snapshot.json --json
python -m agent_memory export-md --project agent-memory-1 --output .\docs\MEMORY.generated.md --json
```

On another computer, restore the ignored local database with:

```powershell
python -m agent_memory init --db .\.agent-memory\memory.db --json
python -m agent_memory import-json .\docs\agent-memory.snapshot.json --db .\.agent-memory\memory.db --json
```

See `docs/MEMORY_SYNC.md` for the full workflow. See `docs/DOCTOR.md` for diagnostics.

## Development

Run tests inside the venv:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The smoke tests can also run without pytest:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```
