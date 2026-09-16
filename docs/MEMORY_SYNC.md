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
  --verify `
  --json

python -m agent_memory export-md `
  --db .\.agent-memory\memory.db `
  --project agent-memory-1 `
  --output .\docs\MEMORY.generated.md `
  --json
```

Review both tracked exports before committing. The JSON snapshot is useful for rebuilding a database, and `--verify` confirms that it restores into a temporary database. The Markdown export is useful for code review and quick reading.

## Restore on Another Computer

After cloning the repository and setting up the Python environment, dry-run the tracked snapshot first, then restore the local database:

```powershell
python -m agent_memory import-json .\docs\agent-memory.snapshot.json `
  --db .\.agent-memory\memory.db `
  --dry-run `
  --json

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
python -m agent_memory import-json ./docs/agent-memory.snapshot.json --db ./.agent-memory/memory.db --dry-run --json
python -m agent_memory init --db ./.agent-memory/memory.db --json
python -m agent_memory import-json ./docs/agent-memory.snapshot.json --db ./.agent-memory/memory.db --json
python -m agent_memory search "canonical memory store" --db ./.agent-memory/memory.db --project agent-memory-1 --limit 5 --json
```

## Snapshot Rules

- The snapshot format is `agent-memory.snapshot.v1`.
- Snapshots contain semantic `memories` and the current exact `mirrored_files` content per project and path. CLI import restores SQLite rows and creates missing mirrored `.md` files under the project root.
- Existing Markdown with matching normalized content is left alone. Differing content prompts for overwrite in an interactive terminal; noninteractive imports skip and report conflicts. Use `--overwrite-files` for explicit unattended replacement or `--no-restore-files` for database-only import. `--dry-run` never writes files or prompts.
- Keyed memories are idempotent on import because they upsert by `project + scope + kind + memory_key`.
- Mirrored files upsert on import by `project + path`. Older snapshots with several revisions per path import the highest-ID revision.
- Schema version 2 keeps one mirror row per path. The first write to a version 1 database creates a sibling `memory.db.schema-v1-*.bak` backup before migrating; retain that file until the migrated database and export are verified. Version 1 cannot identify a later A → B → A return to A, so verify migrated content against Git or the live file when available.
- `import-json --dry-run` validates and classifies the restore without creating or mutating the target database.
- `export-json --verify` writes the snapshot, restores it into a temporary database beside the snapshot, reports restore counts, and removes the temporary database.
- Unkeyed memories are imported as new rows each time; validation reports a warning when they are present. Shared durable memories should use stable keys.
- Import validates content hashes when a snapshot includes them.
- Do not put secrets, credentials, tokens, private keys, or protected personal data in memory or exports.

## Skill Sharing Idea

A future Codex skill could package agent bootstrap instructions plus a memory snapshot restore workflow for developers who want the same project context. That should wait until the JSON snapshot format has been used for a while and remains stable. For now, the tracked JSON snapshot and `AGENTS.md` instructions are the simplest portable workflow.
