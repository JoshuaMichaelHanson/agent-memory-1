# Production Usage Guide

This guide describes how to use `agent-memory` responsibly in real application repositories. The recommended default is a globally installed CLI with one project-local SQLite database per repository.

## Operating Model

- Install the CLI once, preferably through an isolated tool environment such as `pipx`.
- Keep each repository's durable memory in `.agent-memory/memory.db`.
- Keep the live SQLite database out of Git.
- Commit reviewed exports only:
  - `docs/agent-memory.snapshot.json` for machine restore.
  - `docs/MEMORY.generated.md` for human review.
- Treat memory as advisory context. Current user instructions, current repository files, production incident data, security policy, and source code always override stored memory.

This model keeps project context reproducible without letting unrelated repositories silently share state.

## What To Store

Store durable information that a future agent or developer would otherwise have to rediscover.

Good candidates:

- Architecture decisions and why alternatives were rejected.
- Production constraints that affect implementation choices.
- Stable commands for build, test, lint, packaging, local services, and diagnostics.
- Non-obvious setup steps.
- Known workarounds with the reason they exist and when to remove them.
- Project conventions that are not already obvious from code or tooling.
- Links or paths to canonical internal docs, without copying sensitive content into memory.
- Summaries of prior debugging outcomes when they will prevent repeated investigation.

Prefer keyed memories for shared project state so later writes update the same record:

```powershell
agent-memory put `
  --project my-service `
  --kind decision `
  --key api-versioning-policy `
  --content "Use URL path versioning for public APIs because existing gateway routing and partner documentation depend on /v1 and /v2 prefixes." `
  --importance 5 `
  --tag architecture `
  --tag api `
  --agent codex `
  --json
```

## What Not To Store

Do not store:

- Passwords, API keys, access tokens, private keys, certificates, session cookies, or credentialed URLs.
- Production secrets, connection strings with credentials, or `.env` file contents.
- Protected personal data, customer data, medical data, financial account data, or regulated records.
- Incident details that policy says must stay in an approved system of record.
- Routine command output, transient logs, stack traces that are not durable, or temporary notes.
- Guesses, stale plans, or unresolved speculation presented as fact.
- Large file contents that are already tracked by Git and easy to inspect directly.
- Instructions that override the user, repository, security rules, or source of truth systems.

Secret detection is best-effort only. Review memory content and tracked exports before committing.

## Production-Safe Examples

Decision memory:

```powershell
agent-memory put `
  --project billing-api `
  --kind decision `
  --key idempotency-storage `
  --content "Store payment idempotency keys in the primary relational database, not Redis, because retry correctness must survive cache eviction and service restarts." `
  --importance 5 `
  --tag payments `
  --tag reliability `
  --agent codex `
  --json
```

Architecture memory:

```powershell
agent-memory put `
  --project billing-api `
  --kind architecture `
  --key event-publication-flow `
  --content "Domain events are written in the same transaction as aggregate changes and published asynchronously by the outbox worker." `
  --importance 5 `
  --tag outbox `
  --tag events `
  --agent codex `
  --json
```

Constraint memory:

```powershell
agent-memory put `
  --project billing-api `
  --kind constraint `
  --key no-breaking-partner-fields `
  --content "Partner response fields marked deprecated must remain readable until the partner migration tracker confirms all consumers have moved." `
  --importance 4 `
  --tag compatibility `
  --tag partners `
  --agent codex `
  --json
```

Command memory:

```powershell
agent-memory put `
  --project billing-api `
  --kind command `
  --key test-suite `
  --content "Run unit tests with `python -m pytest`; run integration tests only after local service containers are started with the repository's documented compose file." `
  --importance 4 `
  --tag tests `
  --agent codex `
  --json
```

Workaround memory:

```powershell
agent-memory put `
  --project billing-api `
  --kind workaround `
  --key legacy-decimal-rounding `
  --content "Keep legacy half-up decimal rounding in invoice totals until the accounting reconciliation job and partner exports are migrated together." `
  --importance 4 `
  --tag accounting `
  --tag migration `
  --agent codex `
  --json
```

## Repository Bootstrap

For Codex-style agent instructions, install a managed section:

```powershell
agent-memory install-instructions `
  --project my-service `
  --output .\AGENTS.md `
  --json
```

For Claude-style instructions, target `CLAUDE.md`:

```powershell
agent-memory install-instructions `
  --project my-service `
  --output .\CLAUDE.md `
  --json
```

Review the inserted section before committing. The section tells agents how to discover available commands with `agent-memory --help` and `agent-memory <command> --help`.

If a repository uses hand-written instructions instead of the installer, include this minimum workflow:

```markdown
## Persistent Project Memory

Use `agent-memory` for durable project context.

- Search before substantial work: `agent-memory search "<topic>" --project "my-service" --limit 8 --json`.
- Store durable decisions, constraints, commands, and workarounds with stable keys.
- Do not store secrets, credentials, tokens, private keys, customer data, or temporary logs.
- Treat memory as advisory. Current user instructions and repository files override stored memory.
- Before checkin, run `agent-memory export-json --project "my-service" --output docs/agent-memory.snapshot.json --verify --json` and `agent-memory export-md --project "my-service" --output docs/MEMORY.generated.md --json`.
```

## Markdown Mirroring

`mirror-file` stores exact UTF-8 file revisions in SQLite. It does not watch files, summarize content, or auto-track future changes. Run it again when a mirrored file changes.

Mirror files that carry compact, durable project guidance:

- `AGENTS.md`
- `CLAUDE.md`
- `README.md` when it contains setup or architecture guidance agents should search.
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md` or ADR indexes.
- `docs/OPERATIONS.md`, `docs/RUNBOOK.md`, or similar operational guidance after sensitivity review.
- `docs/MEMORY_SYNC.md` when memory export and restore workflow is part of onboarding.

Usually do not mirror:

- Generated exports such as `docs/MEMORY.generated.md`.
- The JSON snapshot itself.
- Large generated docs, API reference output, coverage reports, build logs, or vendor files.
- Files containing secrets, private operational details, or protected personal data.

Example:

```powershell
agent-memory mirror-file .\AGENTS.md --project my-service --agent codex --json
agent-memory mirror-file .\docs\ARCHITECTURE.md --project my-service --agent codex --json
```

After mirroring meaningful changes, export the JSON snapshot so another computer can restore the current mirrored content in SQLite:

```powershell
agent-memory export-json --project my-service --output .\docs\agent-memory.snapshot.json --verify --json
```

## SQLite Versus Markdown

Use SQLite for durable, searchable project memory. Use Markdown for human-readable instructions, review, and bootstrap.

SQLite should replace ad hoc memory Markdown when:

- The information is meant to be searched and updated by agents.
- Multiple agents or sessions need stable keyed records.
- The repository needs a portable restore artifact.
- You need separate memories by kind, scope, tags, importance, and source agent.

Keep hand-written Markdown when:

- Humans need to read or edit the source directly.
- The file is already the repository's canonical instruction or architecture document.
- The content is better maintained in prose than individual keyed records.
- The file is part of normal code review.

Generated Markdown exports are review artifacts, not canonical state.

## Cross-Project Reuse

Keep project-local memory as the default for production repositories. Use reusable project names such as `global`, `personal-patterns`, or `org-patterns` only when the user explicitly wants shared context.

Search current project memory first. Search reusable contexts only as a second step:

```powershell
agent-memory search "database migration" --project my-service --limit 8 --json
agent-memory search "database migration" --db "$env:USERPROFILE\.agent-memory\global-memory.db" --project personal-patterns --limit 5 --json
```

Promote selected memories explicitly with `copy`:

```powershell
agent-memory copy --from-project my-service --from-kind decision --from-key idempotency-storage --to-project personal-patterns --agent codex --json
```

Do not use global memory to override repository-specific instructions, source code, security policy, or team conventions. See `docs/CROSS_PROJECT_MEMORY.md` for the full workflow.

## Review Before Checkin

Before committing memory changes:

```powershell
agent-memory doctor --project my-service --json

agent-memory export-json `
  --project my-service `
  --output .\docs\agent-memory.snapshot.json `
  --verify `
  --json

agent-memory export-md `
  --project my-service `
  --output .\docs\MEMORY.generated.md `
  --json
```

Review the tracked diff for:

- Secret or personal-data exposure.
- Stale or speculative memories.
- Obsolete decisions that should be updated instead of duplicated.
- Unkeyed memories that may duplicate on import.
- Mirrored files that should not be shared through Git.

On another computer, restore with:

```powershell
agent-memory import-json .\docs\agent-memory.snapshot.json --db .\.agent-memory\memory.db --dry-run --json
agent-memory init --db .\.agent-memory\memory.db --json
agent-memory import-json .\docs\agent-memory.snapshot.json --db .\.agent-memory\memory.db --json
```

Run the import from the project root so mirrored Markdown is restored there. If a tracked file differs from the snapshot, an interactive terminal prompts before overwriting; noninteractive imports report and skip conflicts. Use `--overwrite-files` only when the snapshot should replace those files, or `--no-restore-files` for database-only restore.

## Developer Only Testing

This section is for early testing by a small developer group. Remove it before sharing the project broadly.

### Local `pipx` Install Without GitHub

The package can be installed with `pipx` without GitHub, CI, or GitHub Actions. The current `pyproject.toml` defines the installable command:

```toml
[project.scripts]
agent-memory = "agent_memory.cli:main"
```

Install directly from a local checkout:

```powershell
pipx install C:\path\to\agent-memory-1
agent-memory --help
```

Reinstall after local changes:

```powershell
pipx install --force C:\path\to\agent-memory-1
```

A local Git repository can also be installed without GitHub:

```powershell
pipx install git+file:///C:/path/to/agent-memory-1
```

### Build A Wheel Locally

A better pre-release test is to build a wheel and install that same artifact elsewhere:

```powershell
.\.venv\Scripts\python.exe -m pip install build
.\.venv\Scripts\python.exe -m build
```

The wheel should appear under `dist\` with a name like:

```text
agent_memory-0.2.0-py3-none-any.whl
```

`py3-none-any` means the package is pure Python and should install on Windows, macOS, and Linux. Copy the wheel to the other computer and install it:

```sh
pipx install --force ./agent_memory-0.2.0-py3-none-any.whl
agent-memory --help
```

Use `--force` during repeated testing of the same build, or bump the version in `pyproject.toml` for the next release.

### Windows Build To macOS Install

Building the wheel on Windows 11 and installing it on macOS is expected to work because `agent-memory` is pure Python and has no compiled extensions.

The wheel does not bundle Python. It bundles the `agent-memory` package code and metadata only. The target Mac must already have a compatible Python installed.

The package currently requires Python 3.11 or newer:

```toml
requires-python = ">=3.11"
```

On macOS, check Python first:

```sh
python3 --version
pipx --version
```

Install with the default `python3` if it is 3.11 or newer:

```sh
pipx install --force --python python3 ./agent_memory-0.2.0-py3-none-any.whl
```

If the Mac has multiple Python versions, be explicit:

```sh
pipx install --force --python python3.12 ./agent_memory-0.2.0-py3-none-any.whl
```

or use the full Homebrew path when needed:

```sh
pipx install --force --python /opt/homebrew/bin/python3.12 ./agent_memory-0.2.0-py3-none-any.whl
```

The important distinction is:

- The wheel carries the package code and Python compatibility metadata.
- `pipx` creates an isolated virtual environment on the target computer.
- The target computer's Python actually runs the CLI.

### Confirm FTS5 On macOS

After installing on macOS, run:

```sh
agent-memory status --project test-project --json
```

Confirm the JSON output reports:

```json
"search_backend": "fts5"
```

If it reports this instead, SQLite still works but Python's bundled SQLite does not have FTS5 enabled, so `agent-memory` is using the fallback search path:

```json
"search_backend": "like"
```

The fuller diagnostic command also reports the active backend:

```sh
agent-memory doctor --project test-project --json
```

Look for the `fts_backend` check. A healthy FTS5 setup reports a message like:

```json
{
  "name": "fts_backend",
  "status": "pass",
  "message": "Search backend is fts5."
}
```

A quick functional smoke test:

```sh
agent-memory init --project test-project --json

agent-memory put \
  --project test-project \
  --kind decision \
  --key fts5-test \
  --content "FTS5 phrase search should find this sqlite indexing test." \
  --tag sqlite \
  --json

agent-memory search "sqlite indexing" \
  --project test-project \
  --json
```

Confirm the search result includes:

```json
"search_backend": "fts5"
```

If the result uses `like`, the CLI is still usable, but search will use the simpler fallback behavior.
