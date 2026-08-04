# Working Memory

This file is temporary project memory until `agent-memory` can store and search its own SQLite database.

## Current State

- Repository path: `C:\Development\agent-memory-1`.
- Active branch for current work: `feat/phase-6`.
- Git repository has been initialized.
- `.gitignore` ignores IntelliJ, VS Code, Python, JavaScript, Java/JVM, build outputs, and local `.agent-memory` SQLite database files.
- IntelliJ MCP is configured through `.codex/config.toml` using `http://127.0.0.1:64342/stream`.
- The live IntelliJ MCP server resolved this project and reported one Java module named `agent-memory-1`.
- The full implementation spec is in `codex-sqlite-agent-memory-implementation-spec.md`.
- Phase 1 is complete: `pyproject.toml`, `README.md`, `LICENSE`, `src/agent_memory`, and smoke tests exist.
- Phase 2 is complete: `config.py`, `database.py`, `schema.sql`, idempotent `init`, richer `status`, and Phase 2 tests exist.
- Phase 3 is complete: `models.py`, `errors.py`, `service.py`, memory/tag/content normalization, `MemoryService.put`, and the `put` CLI command exist.
- Phase 4 is complete: `MemoryService.get_by_id`, `get_by_key`, touch/no-touch retrieval metadata, `recent`, and the `get`/`recent` CLI commands exist.
- Phase 5 is complete: `MemoryService.search`, FTS5 search, LIKE fallback, malformed FTS retry, search filters, touch/no-touch search metadata, and the `search` CLI command exist.
- Phase 6 is complete: `delete`, `mirror-file`, `export-md`, mirrored file revisions, delete confirmation with `--yes`, and atomic Markdown export exist.
- The local `.agent-memory/memory.db` initializes successfully, reports schema version `1`, WAL journal mode, and FTS5 search backend on this Python build.
- `.venv` can be created with `scripts/setup-dev.ps1`; it installs the project editable with `.[dev]` and pytest. The setup script passed with pytest 9.1.1 on Python 3.14.3 after running outside the sandbox because ensurepip/pip temp-file writes were blocked inside the sandbox.

## Durable Decisions

- Implement the first release as a Python 3.11+ CLI named `agent-memory`.
- Keep runtime dependencies to the Python standard library for version 1.
- Use SQLite as the canonical memory store.
- Keep CLI parsing and output formatting separate from reusable service/database logic.
- Prepare for MCP by making `MemoryService` methods accept normal Python values and return dataclasses or JSON-serializable dictionaries.
- Do not implement the MCP server in version 1.
- Use Markdown files only as bootstrap context and optional generated exports, not as canonical memory after the SQLite database is working.
- Keep tests away from the real user profile and real project database. Current tests use ignored paths under `tmp/tests`.
- `put`, `delete`, `mirror-file`, and `export-md` are write commands and may create or mutate the database/output files. Read-only status/search/get/recent behavior should avoid creating missing databases.
- Default `get` and `search` update `last_accessed_at` and increment `access_count`; use `--no-touch` for inspection without mutation.
- Search uses FTS5 when the table exists and falls back to parameterized LIKE when FTS5 is unavailable. FTS results order by importance descending, FTS rank, updated time, and ID.
- JSON delete requires `--yes`; interactive non-JSON delete prompts when stdin is a terminal.

## Next Task

Start Phase 7 in `docs/BACKLOG.md`: expand README, add AGENTS/CLAUDE bootstrap examples, run the full acceptance command set, and write the final implementation report.

## Migration Target

When `python -m agent_memory init`, keyed `put`, and `search` pass locally, migrate this file's durable facts into `.agent-memory/memory.db` using stable keys.
