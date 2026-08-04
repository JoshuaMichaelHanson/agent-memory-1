# Agent Instructions

This project is bootstrapping a Python CLI named `agent-memory`.

Until the SQLite memory database is usable, persistent working context lives in:

- `codex-sqlite-agent-memory-implementation-spec.md` for the full product specification
- `docs/IMPLEMENTATION_PLAN.md` for staged delivery
- `docs/BACKLOG.md` for actionable tasks
- `docs/SELF_HOSTING_MEMORY_CUTOVER.md` for the point where this repo can use its own SQLite memory
- `WORKING_MEMORY.md` for durable decisions and current repo state before the database exists

Before starting work:

1. Read `WORKING_MEMORY.md`.
2. Check `docs/BACKLOG.md` for the next incomplete task.
3. Use the implementation spec as the source of truth for behavior.

After meaningful work:

1. Update `WORKING_MEMORY.md` with durable facts only.
2. Update `docs/BACKLOG.md` task statuses.
3. Once the CLI can initialize, put, and search memory, follow `docs/SELF_HOSTING_MEMORY_CUTOVER.md` and start using `.agent-memory/memory.db` as canonical memory.

Do not store secrets, credentials, tokens, or protected personal data in docs or memory.
