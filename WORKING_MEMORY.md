# Working Memory

This file is legacy bootstrap context. From Phase 8 onward, SQLite memory is canonical for this checkout.

## Current State

- Repository path: this checkout root.
- Active branch for current work: use `git status --short --branch`.
- The local canonical memory database is `.agent-memory/memory.db`.
- The live SQLite database remains ignored by Git.
- Portable memory handoff uses `docs/agent-memory.snapshot.json` for restore and `docs/MEMORY.generated.md` for human review.
- Restore/export workflow is documented in `docs/MEMORY_SYNC.md`.
- `AGENTS.md` now tells future agents to search `agent-memory` first and use this file only as fallback.
- The database has been initialized, keyed project memories are in use, search/recent have been verified, and tracked memory exports are generated before checkin.

## Durable Decisions Kept Here For Fallback

- SQLite is the canonical memory store for `agent-memory`.
- Markdown files are bootstrap context, optional generated exports, or compatibility artifacts.
- The CLI remains a thin adapter over reusable service/database logic for a future MCP adapter.
- Runtime dependencies stay limited to the Python standard library for version 1.
- Do not commit live `.agent-memory` SQLite database files; commit portable exports instead.
- Use stable keys for shared durable memories so JSON snapshot imports are idempotent.
- Run tests with `.\.venv\Scripts\python.exe -m pytest`.

## Next Task

Use `agent-memory search` and `docs/BACKLOG.md` to choose the next phase. If this file disagrees with SQLite memory or current repo files, prefer SQLite memory and current repo files.
