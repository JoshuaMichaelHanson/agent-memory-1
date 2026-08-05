# agent-memory Implementation Report

## Summary

The version 1 SQLite-backed `agent-memory` CLI is implemented and verified through Phase 7. The CLI can initialize a project-local database, store keyed and unkeyed memories, retrieve them, search with FTS5 or a LIKE fallback, list recent memories, delete obsolete records, mirror Markdown file revisions, and export selected memories to generated Markdown.

SQLite is the canonical memory store. Markdown files are bootstrap snippets, mirrored snapshots, or generated exports only.

## Files Created

- `pyproject.toml`
- `README.md`
- `LICENSE`
- `.gitignore`
- `AGENTS.md`
- `WORKING_MEMORY.md`
- `docs/BACKLOG.md`
- `docs/IMPLEMENTATION_REPORT.md`
- `scripts/setup-dev.ps1`
- `scripts/setup-dev.sh`
- `src/agent_memory/__init__.py`
- `src/agent_memory/__main__.py`
- `src/agent_memory/cli.py`
- `src/agent_memory/config.py`
- `src/agent_memory/database.py`
- `src/agent_memory/errors.py`
- `src/agent_memory/markdown.py`
- `src/agent_memory/models.py`
- `src/agent_memory/schema.sql`
- `src/agent_memory/service.py`
- `tests/conftest.py`
- `tests/test_cli_smoke.py`
- `tests/test_config.py`
- `tests/test_database.py`
- `tests/test_models.py`
- `tests/test_service.py`
- `examples/AGENTS-memory-section.md`
- `examples/CLAUDE-memory-section.md`

## Design Decisions

- Runtime dependencies are limited to the Python standard library.
- Development dependencies are isolated in a local virtual environment through `scripts/setup-dev.ps1` or `scripts/setup-dev.sh`.
- `MemoryService` owns business behavior and returns dataclasses or dictionaries, keeping the CLI thin and MCP-ready.
- Database path resolution is shared and follows `--db`, then `AGENT_MEMORY_DB`, then `<project-root>/.agent-memory/memory.db`.
- Writable database connections apply WAL mode, busy timeout, foreign keys, and synchronous NORMAL.
- FTS5 is used when available; otherwise searches fall back to parameterized LIKE queries.
- Keyed memories upsert on `project + scope + kind + memory_key`; unkeyed memories always insert.
- Generated Markdown exports start with a warning and are written atomically.
- The database and generated local artifacts are ignored by Git by default.

## Commands Tested

The full pytest suite was run:

```text
.\.venv\Scripts\python.exe -m pytest
```

The implementation-spec acceptance flow was run against a temporary database under `tmp/acceptance-phase7-20260804-153059/`:

```text
python -m agent_memory init --db <tmp>\memory.db --json
python -m agent_memory put --db <tmp>\memory.db --project demo --kind decision --key database-choice --content "Use SQLite as the canonical agent memory store." --tag sqlite --tag architecture --importance 5 --agent codex --json
python -m agent_memory put --db <tmp>\memory.db --project demo --kind decision --key database-choice --content "Use SQLite as the canonical store and generate Markdown only for inspection." --tag sqlite --tag architecture --importance 5 --agent claude --json
python -m agent_memory search "canonical SQLite" --db <tmp>\memory.db --project demo --limit 5 --json
python -m agent_memory mirror-file <tmp>\AGENTS.md --db <tmp>\memory.db --project demo --agent codex --json
python -m agent_memory mirror-file <tmp>\AGENTS.md --db <tmp>\memory.db --project demo --agent codex --json
python -m agent_memory export-md --db <tmp>\memory.db --project demo --output <tmp>\MEMORY.generated.md --json
```

## Test Results

- Pytest: 47 passed after Phase 8 snapshot import/export tests.
- Acceptance: passed.
- Search backend in the acceptance run: FTS5.
- Known local warning: pytest reports a non-failing cache warning for `.pytest_cache` on this Windows checkout.

## Known Limitations

- No MCP server is included in version 1.
- No vector embeddings, semantic search, HTTP API, background daemon, encryption, cloud sync, or GUI are included.
- The tool does not attempt comprehensive secret detection; users and agents must avoid storing secrets or protected personal data.
- Markdown mirroring stores exact file revisions only and does not extract semantic memories.
- Generated Markdown exports are review artifacts, not authoritative state.

## Next MCP Step

Add an optional MCP adapter that depends on the official Python MCP package through an optional extra such as `agent-memory[mcp]`. The adapter should instantiate `MemoryService`, expose MCP tools like `memory_put`, `memory_search`, and `memory_export_markdown`, and return the same JSON-safe structures already used by the CLI. It should not shell out to the CLI or duplicate SQL.

## Phase 8 Addendum

Phase 8 added dogfooding support without committing the live SQLite database:

- Added `export-json` for restorable `agent-memory.snapshot.v1` files.
- Added `import-json` for recreating or updating a local SQLite database from a tracked snapshot.
- Documented the before-checkin export workflow in `docs/MEMORY_SYNC.md`.
- Seeded `.agent-memory/memory.db` with keyed project memories.
- Generated `docs/agent-memory.snapshot.json` for machine restore.
- Generated `docs/MEMORY.generated.md` for human review.

The live database remains ignored by Git. The tracked JSON snapshot is the portable restore artifact.

## Production Readiness Roadmap

Next work is documented in docs/PRODUCTION_READINESS_ROADMAP.md. After Phase 12, the order is agent onboarding instructions, production usage guide, cross-project/global memory sharing, Codex and Claude skill templates, schema migration framework, and CI/release validation. MCP remains future-state and optional.

## Phase 9 Addendum

Phase 9 added best-effort secret guardrails for `put`, `mirror-file`, and `import-json`. Sensitive-looking content is blocked by default with a validation error, and `--allow-sensitive` is available for intentional local-only storage. Scanner details are documented in `docs/SECRET_GUARDRAILS.md`.

## Phase 10 Addendum

Phase 10 added `agent-memory doctor`, a diagnostic command that reports setup health separately from command execution. It checks database path resolution, existence, schema version, WAL, search backend, read/write viability, live DB ignore policy, tracked exports, and JSON snapshot restore. Details are documented in `docs/DOCTOR.md`.

## Phase 11 Addendum

Phase 11 completed JSON snapshot coverage for mirrored file revisions. `export-json` now writes a `mirrored_files` array, and `import-json` restores those revisions idempotently by `project + path + content_sha256`. Snapshot workflow details are documented in `docs/MEMORY_SYNC.md`.

## Phase 12 Addendum

Phase 12 polished backup and restore workflows. `import-json --dry-run` validates snapshots and classifies expected inserts, updates, unchanged rows, unkeyed inserts, and mirrored file imports without mutating the target database. Snapshot validation reports all detected item-level problems before mutation. `export-json --verify` restores the written snapshot into a temporary SQLite database and reports restore counts. Unkeyed memories now produce validation warnings because repeated real imports create new rows. The roadmap was also updated so the next phases are agent onboarding instructions, production usage guide, cross-project/global memory sharing, Codex and Claude skill templates, schema migrations, and CI/release validation.

## Phase 13 Addendum

Phase 13 added agent onboarding commands for global CLI discovery. `agent-memory instructions` prints concise agent-facing Markdown, `agent-memory instructions --json` returns machine-readable instruction metadata, and `agent-memory install-instructions` installs or replaces a managed section in files such as `AGENTS.md` while preserving hand-written content outside the markers. Details are documented in `docs/AGENT_ONBOARDING.md`.

## Phase 14 Addendum

Phase 14 added production usage guidance for real application repositories. `docs/PRODUCTION_USAGE.md` documents the recommended global CLI plus project-local database model, what to store, what not to store, advisory-only memory rules, production-safe examples, repository bootstrap snippets, explicit Markdown mirroring, SQLite-versus-Markdown guidance, and review-before-checkin workflow.
## Phase 15 Addendum

Phase 15 added explicit cross-project memory sharing. `agent-memory copy` copies one selected memory by ID or keyed source lookup into another project in the same database while requiring `--to-key` for unkeyed sources. `docs/CROSS_PROJECT_MEMORY.md` documents project-local memory as the default, global databases as advanced personal mode, reusable project naming conventions, explicit multi-context search, copy/promotion workflow, snapshot sharing, and privacy/context-bleed risks.