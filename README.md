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
- `instructions`
- `install-instructions`
- `put`
- `get`
- `search`
- `recent`
- `copy`
- `delete`
- `mirror-file`
- `export-md`
- `export-json`
- `import-json`

Phase 16 adds copyable Codex and Claude skill templates for teaching agents to use a global `agent-memory` CLI.

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

### GitHub User Install

For the first small-group GitHub share, install from the repository URL:

```powershell
pipx install git+https://github.com/JoshuaMichaelHanson/agent-memory-1.git@main
```

For private repositories or SSH access:

```powershell
pipx install git+ssh://github.com/JoshuaMichaelHanson/agent-memory-1.git@main
```

Refresh after repository changes:

```powershell
pipx install --force git+https://github.com/JoshuaMichaelHanson/agent-memory-1.git@main
```

From a local checkout:

```powershell
pipx install .
```

If the app is later published to PyPI:

```powershell
pipx install agent-memory
```

## Quick Start

PowerShell
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

PowerShell
```powershell
agent-memory init --db .\.agent-memory\memory.db --json
```
POSIX
```bash
agent-memory init --db ./.agent-memory/memory.db --json
```

### `status`

Reports database path, existence, schema version, memory count, journal mode, and search backend.

PowerShell
```powershell
agent-memory status --project demo --json
```
POSIX
```bash
agent-memory status --project demo --json
```

### `doctor`

Diagnoses database health, ignored live DB files, tracked exports, and snapshot restore viability. `ok` means the command ran; `healthy` reports setup health.

```powershell
agent-memory doctor --project demo --json
```

### `instructions`

Prints agent-facing Markdown instructions for using the CLI in a project. JSON mode returns the same guidance as machine-readable metadata.

```powershell
agent-memory instructions --project demo
agent-memory instructions --project demo --json
```

### `install-instructions`

Installs or updates a managed `agent-memory` section in an agent instruction file such as `AGENTS.md`. Existing managed sections are replaced by marker; hand-written content outside the markers is preserved.

PowerShell
```powershell
agent-memory install-instructions --project demo --output .\AGENTS.md --json
```
POSIX
```bash
agent-memory install-instructions --project demo --output ./AGENTS.md --json
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

### `copy`

Copies one selected memory into another project in the same database. Copy by ID or keyed source lookup. The target scope, kind, and key default from the source; copying an unkeyed source requires `--to-key`.

```powershell
agent-memory copy --from-project demo --from-kind decision --from-key database-choice --to-project personal-patterns --agent codex --json
agent-memory copy --id 42 --to-project global --to-key reusable-pattern --agent codex --json
```

### `delete`

Deletes by ID or compound key. Use `--yes` in scripts and agent workflows.

```powershell
agent-memory delete --id 1 --yes --json
agent-memory delete --project demo --kind decision --key database-choice --yes --json
```

### `mirror-file`

Stores the current exact UTF-8 content for each project and path in `mirrored_files`. Changed content updates the same row; Git can retain revision history. It does not extract semantic memories. By default, mirrored file content is checked for best-effort sensitive-value patterns.

```powershell
agent-memory mirror-file .\AGENTS.md --project demo --agent codex --json
```

### `export-md`

Writes a generated Markdown export atomically for human review.

```powershell
agent-memory export-md --project demo --output .\docs\MEMORY.generated.md --json
```

### `export-json`

Writes a machine-restorable JSON snapshot. Use `--verify` before check-in to restore the written snapshot into a temporary database and report restore counts.

```powershell
agent-memory export-json --project demo --output .\docs\agent-memory.snapshot.json --verify --json
```

### `import-json`

Imports a JSON snapshot into the configured SQLite database and recreates missing mirrored Markdown files under the project root. Existing files with the same normalized content are left alone. A differing file triggers an interactive overwrite prompt; noninteractive runs skip it and report the conflict. Use `--overwrite-files` to explicitly replace differing files without a prompt, or `--no-restore-files` for database-only import. `--dry-run` validates and classifies without writing or prompting. Keyed memories are idempotent; unkeyed memories import as new rows on each real import. Imported content is checked for best-effort sensitive-value patterns.

```powershell
agent-memory import-json .\docs\agent-memory.snapshot.json --dry-run --json
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

## Cross-Project and Global Memory

Project-local databases remain the recommended default. For reusable context, use explicit project names such as `global`, `personal-patterns`, or `org-patterns`, and search them only when the current project memory is insufficient. Use `copy` to promote a selected memory into another project instead of making repositories silently inherit global context.

See `docs/CROSS_PROJECT_MEMORY.md` for the full workflow and privacy tradeoffs.

## Markdown Mirroring and Export

`mirror-file` stores one current UTF-8 snapshot per project and path. Repeated identical content is unchanged; changed content updates the row. It does not summarize Markdown or convert sections into semantic memories. JSON import restores mirrored `.md` files as described above; paths outside the project root and non-Markdown paths are not written to disk.

`export-md` writes generated Markdown for human review. The generated file starts with a warning and should not be treated as canonical.

`export-json` writes the portable restore artifact, including semantic memories and current mirrored files. `export-json --verify` restores the written artifact into a temporary SQLite database and reports restore counts. `import-json --dry-run` validates and classifies a restore without mutation. Keyed memories are idempotent; mirrored files upsert by `project + path`; unkeyed memories import as new rows on every real import. Legacy snapshots containing multiple mirror revisions import the highest-ID revision for each path.

## Security and Privacy

Do not store passwords, API keys, access tokens, private keys, credentialed connection strings, or protected personal data.

Phase 9 adds best-effort secret guardrails for `put`, `mirror-file`, and `import-json`. The scanner blocks obvious private key blocks, credentialed URLs, bearer tokens, secret-like assignments such as `password=...`, and common token formats. Detection is not comprehensive and is not a substitute for review. Use `--allow-sensitive` only for rare intentional local-only storage.

The database is a normal local file and inherits operating-system permissions. Project-local databases should normally be excluded from Git. Generated Markdown exports may expose the same information as the database.

Stored memory is advisory context. Current user instructions and current repository files override stored memory.

## Agent Bootstrap Examples

Reusable snippets are available in:

- `examples/AGENTS-memory-section.md`
- `examples/CLAUDE-memory-section.md`

## Agent Skill Templates

Copyable skill templates are available for agents that support reusable skills:

- `examples/codex-skill-template/agent-memory/SKILL.md`
- `examples/claude-skill-template/agent-memory/SKILL.md`

See `docs/AGENT_MEMORY_SKILL_TEMPLATES.md` for install paths, expected workflows, safety rules, and test prompts.

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
python -m agent_memory export-json --project agent-memory-1 --output .\docs\agent-memory.snapshot.json --verify --json
python -m agent_memory export-md --project agent-memory-1 --output .\docs\MEMORY.generated.md --json
```

On another computer, restore the ignored local database with:

```powershell
python -m agent_memory import-json .\docs\agent-memory.snapshot.json --db .\.agent-memory\memory.db --dry-run --json
python -m agent_memory init --db .\.agent-memory\memory.db --json
python -m agent_memory import-json .\docs\agent-memory.snapshot.json --db .\.agent-memory\memory.db --json
```

See `docs/MEMORY_SYNC.md` for the full workflow. See `docs/DOCTOR.md` for diagnostics. See `docs/AGENT_ONBOARDING.md` for global CLI agent-bootstrap guidance. See `docs/PRODUCTION_USAGE.md` for production-safe memory practices, repository bootstrap examples, and Markdown mirroring guidance. See `docs/CROSS_PROJECT_MEMORY.md` for explicit cross-project and global memory workflows. See `docs/AGENT_MEMORY_SKILL_TEMPLATES.md` for Codex and Claude skill templates.

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
