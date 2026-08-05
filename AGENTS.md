# Agent Instructions

This project dogfoods the Python CLI named `agent-memory`.

Persistent project memory is stored in the local SQLite database:

- `.agent-memory/memory.db`

The live database is ignored by Git. Portable memory handoff uses tracked exports:

- `docs/agent-memory.snapshot.json` for machine restore
- `docs/MEMORY.generated.md` for human review
- `docs/MEMORY_SYNC.md` for export and restore commands

Before starting work:

1. Run `python -m agent_memory status --project agent-memory-1 --json`.
2. If the database is missing and `docs/agent-memory.snapshot.json` exists, run `python -m agent_memory import-json .\docs\agent-memory.snapshot.json --db .\.agent-memory\memory.db --json`.
3. Search memory for the current task with `python -m agent_memory search "<task topic>" --project agent-memory-1 --limit 8 --json`.
4. Read `docs/BACKLOG.md` for the next incomplete task.
5. Use `codex-sqlite-agent-memory-implementation-spec.md` as the source of truth for product behavior.
6. Use `WORKING_MEMORY.md` only as legacy bootstrap context when the database or snapshot is unavailable.

After meaningful work:

1. Store durable facts with stable keys using `python -m agent_memory put --project agent-memory-1 ... --json`.
2. Update `docs/BACKLOG.md` task statuses.
3. Export memory before checkin:
   - `python -m agent_memory export-json --project agent-memory-1 --output .\docs\agent-memory.snapshot.json --json`
   - `python -m agent_memory export-md --project agent-memory-1 --output .\docs\MEMORY.generated.md --json`
4. Review tracked exports before committing.

Current user instructions and current repository files override stored memory. Do not store secrets, credentials, tokens, private keys, or protected personal data in docs or memory.
