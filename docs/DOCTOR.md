# Doctor Command

`agent-memory doctor` diagnoses the local memory setup without treating a degraded setup as a command failure.

## Usage

```powershell
python -m agent_memory doctor --project agent-memory-1 --json
```

With a custom database path:

```powershell
python -m agent_memory doctor `
  --db .\.agent-memory\memory.db `
  --project agent-memory-1 `
  --json
```

## JSON Shape

The command returns `ok: true` when the diagnostic command ran successfully. Setup health is reported separately:

```json
{
  "ok": true,
  "healthy": false,
  "failure_count": 1,
  "warning_count": 2,
  "checks": [],
  "failures": [],
  "warnings": []
}
```

This lets scripts distinguish command execution from environment health.

## Checks

The doctor checks:

- database path resolution
- database parent write access
- database existence
- schema initialization and version
- WAL journal mode
- FTS or LIKE search backend
- read-only database inspection
- `.gitignore` policy for live SQLite files
- tracked JSON snapshot presence
- tracked Markdown export presence
- JSON snapshot restore into an ignored temporary database under `tmp/`

Warnings indicate setup choices or missing optional artifacts that may still be workable. Failures indicate the local setup is not ready for normal memory use.
