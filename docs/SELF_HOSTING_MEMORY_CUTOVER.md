# Self-Hosting Memory Cutover

This project should switch from Markdown working memory to SQLite memory as soon as the CLI can reliably initialize, put keyed memories, retrieve, and search.

## Minimum Required Commands

These commands must work before cutover:

```powershell
python -m agent_memory init --db .\.agent-memory\memory.db --json
python -m agent_memory put --db .\.agent-memory\memory.db --project agent-memory-1 --kind decision --key sqlite-canonical-store --content "SQLite is the canonical memory store for agent-memory; Markdown is only bootstrap context or generated export." --importance 5 --agent codex --json
python -m agent_memory search "canonical memory store" --db .\.agent-memory\memory.db --project agent-memory-1 --limit 5 --json
```

Optional after package installation:

```powershell
agent-memory status --project agent-memory-1 --json
```

## Seed Memories

Insert these durable memories during cutover.

### project-state

- Kind: `environment`
- Importance: `4`
- Tags: `bootstrap,repo,intellij`
- Content:

```text
Repository path is C:\Development\agent-memory-1. Git is initialized. IntelliJ MCP is configured in .codex/config.toml and resolved the project as module agent-memory-1.
```

### sqlite-canonical-store

- Kind: `decision`
- Importance: `5`
- Tags: `sqlite,memory,architecture`
- Content:

```text
SQLite is the canonical memory store for agent-memory. Markdown files are only bootstrap context, optional generated exports, or compatibility artifacts.
```

### cli-service-separation

- Kind: `architecture`
- Importance: `5`
- Tags: `cli,mcp,service`
- Content:

```text
The CLI must remain a thin adapter over reusable service/database logic so a future MCP server can call MemoryService directly without shelling out or duplicating SQL.
```

### bootstrap-docs-before-db

- Kind: `workflow`
- Importance: `4`
- Tags: `bootstrap,docs`
- Content:

```text
Before the SQLite database is usable, use WORKING_MEMORY.md and docs/BACKLOG.md as temporary durable context. After cutover, write durable memory to SQLite first.
```

### local-db-gitignore

- Kind: `constraint`
- Importance: `4`
- Tags: `gitignore,privacy,sqlite`
- Content:

```text
Do not commit the local .agent-memory SQLite database files. .gitignore excludes memory.db, memory.db-shm, memory.db-wal, and .agent-memory/*.tmp.
```

## Post-Cutover AGENTS.md Change

After the seed memories are searchable, update `AGENTS.md` so future agents do this first:

```powershell
python -m agent_memory status --project agent-memory-1 --json
python -m agent_memory search "<task topic>" --project agent-memory-1 --limit 8 --json
python -m agent_memory recent --project agent-memory-1 --limit 5 --json
```

Keep the rule that current user instructions and repository files override stored memory.

## Cutover Is Complete When

- `status --json` reports the local database exists.
- `search` returns at least one seeded memory.
- `recent` returns the seeded memories.
- `WORKING_MEMORY.md` says SQLite memory is canonical from that point forward.
- New durable decisions are written with stable keys using `put`.
