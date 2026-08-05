# Memory Export and Restore

The live SQLite database in `.agent-memory/memory.db` is local working state and stays ignored by Git. Share project memory through tracked exports instead.

## Tracked Files

- `docs/agent-memory.snapshot.json` is the machine-restorable snapshot.
- `docs/MEMORY.generated.md` is the human-readable review export.
- `.agent-memory/memory.db`, `.agent-memory/memory.db-shm`, and `.agent-memory/memory.db-wal` are local runtime files and should not be committed.

## Before Checkin

Run these commands after meaningful memory changes and before committing:

```powershell
python -m agent_memory export-json `
  --db .\.agent-memory\memory.db `
  --project agent-memory-1 `
  --output .\docs\agent-memory.snapshot.json `
  --json

python -m agent_memory export-md `
  --db .\.agent-memory\memory.db `
  --project agent-memory-1 `
  --output .\docs\MEMORY.generated.md `
  --json
```

Review both tracked exports before committing. The JSON snapshot is useful for rebuilding a database. The Markdown export is useful for code review and quick reading.

## Restore on Another Computer

After cloning the repository and setting up the Python environment, restore the local database from the tracked JSON snapshot:

```powershell
python -m agent_memory init --db .\.agent-memory\memory.db --json

python -m agent_memory import-json .\docs\agent-memory.snapshot.json `
  --db .\.agent-memory\memory.db `
  --json

python -m agent_memory search "canonical memory store" `
  --db .\.agent-memory\memory.db `
  --project agent-memory-1 `
  --limit 5 `
  --json
```

POSIX shell:

```sh
python -m agent_memory init --db ./.agent-memory/memory.db --json
python -m agent_memory import-json ./docs/agent-memory.snapshot.json --db ./.agent-memory/memory.db --json
python -m agent_memory search "canonical memory store" --db ./.agent-memory/memory.db --project agent-memory-1 --limit 5 --json
```

## Snapshot Rules

- The snapshot format is `agent-memory.snapshot.v1`.
- Snapshots contain semantic `memories` and exact `mirrored_files` revisions.
- Keyed memories are idempotent on import because they upsert by `project + scope + kind + memory_key`.
- Mirrored file revisions are idempotent on import by `project + path + content_sha256`.
- Unkeyed memories are imported as new rows each time. Shared durable memories should use stable keys.
- Import validates content hashes when a snapshot includes them.
- Do not put secrets, credentials, tokens, private keys, or protected personal data in memory or exports.

## Skill Sharing Idea

A future Codex skill could package agent bootstrap instructions plus a memory snapshot restore workflow for developers who want the same project context. That should wait until the JSON snapshot format has been used for a while and remains stable. For now, the tracked JSON snapshot and `AGENTS.md` instructions are the simplest portable workflow.
