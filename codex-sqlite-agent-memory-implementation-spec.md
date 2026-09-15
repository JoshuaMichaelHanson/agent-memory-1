# SQLite Agent Memory CLI
## Codex Implementation Specification

Build a small, reliable, cross-platform Python CLI that stores durable AI-agent memory in SQLite.

The first version must be easy for Codex, Claude Code, or a human to call from a terminal. The core logic must be separated from the CLI so the same service can later be exposed through a Model Context Protocol server without rewriting the database or business logic.

---

# 1. Goal

Create an `agent-memory` command-line application that lets an AI coding agent:

- initialize a project-local memory database
- store durable memories
- update an existing keyed memory instead of creating duplicates
- retrieve a memory by ID or key
- search memories using SQLite full-text search
- list recent or important memories
- delete obsolete memories
- mirror selected Markdown files into SQLite
- export selected memories to a readable Markdown file
- emit machine-readable JSON for future MCP integration

The first release is a CLI, not a full MCP server.

The internal architecture must make a later MCP adapter thin and mechanical. MCP tools should call the same service methods used by the CLI.

---

# 2. Recommended Operating Model

Use a hybrid memory system:

```text
AGENTS.md / CLAUDE.md
        |
        | small bootstrap instructions
        v
agent-memory CLI
        |
        v
.agent-memory/memory.db
        |
        +-- structured memories
        +-- full-text search
        +-- timestamps and importance
        +-- optional Markdown export
```

SQLite is the canonical memory store.

Markdown files may still be used for:

- agent bootstrap instructions
- human-readable exports
- Git review
- compatibility when the CLI is unavailable

Do not treat a generated Markdown export as the authoritative database.

---

# 3. Core Design Principles

1. **SQLite is canonical**
   - The database is the source of truth.
   - Generated Markdown files must state that they are generated.

2. **The CLI is a thin adapter**
   - Argument parsing and output formatting belong in the CLI layer.
   - Database and business rules belong in reusable Python modules.

3. **The service layer is MCP-ready**
   - Public service methods accept normal Python values.
   - Public service methods return dataclasses or JSON-serializable dictionaries.
   - Service methods must not print to stdout.
   - Service methods must not call `argparse`.

4. **Use keyed upserts**
   - A stable `memory_key` lets agents revise a memory instead of endlessly appending contradictory notes.

5. **Retrieve only relevant context**
   - Agents should search for a task topic.
   - Agents should not dump the entire database into their context window.

6. **Keep dependencies minimal**
   - Runtime should use the Python standard library only if practical.
   - `pytest` may be used as a development dependency.
   - A future MCP adapter may add the official Python MCP package as an optional dependency.

7. **Cross-platform behavior**
   - Support Windows, macOS, and Linux.
   - Do not assume Bash.
   - Do not depend on GNU-only command-line tools.

8. **Fail clearly**
   - Return nonzero exit codes on errors.
   - Print concise, actionable errors to stderr.
   - Never silently discard a failed write.

---

# 4. Technology Choices

Use:

- Python 3.11 or newer
- `sqlite3`
- `argparse`
- `dataclasses`
- `pathlib`
- `json`
- `hashlib`
- `datetime`
- `subprocess` only for optional Git-root detection
- `pytest` for tests

Do not use an ORM in the initial implementation.

The application should install an executable named:

```text
agent-memory
```

It should also remain runnable without installation:

```text
python -m agent_memory
```

---

# 5. Suggested Project Structure

```text
agent-memory/
|-- pyproject.toml
|-- README.md
|-- LICENSE
|-- .gitignore
|-- src/
|   `-- agent_memory/
|       |-- __init__.py
|       |-- __main__.py
|       |-- cli.py
|       |-- config.py
|       |-- database.py
|       |-- models.py
|       |-- service.py
|       |-- markdown.py
|       `-- schema.sql
|-- tests/
|   |-- conftest.py
|   |-- test_database.py
|   |-- test_service.py
|   |-- test_cli.py
|   |-- test_search.py
|   `-- test_markdown.py
`-- examples/
    |-- AGENTS-memory-section.md
    `-- CLAUDE-memory-section.md
```

Keep the design compact. Avoid excessive abstraction or a large framework.

---

# 6. Database Location Resolution

Resolve the database path in this order:

1. CLI option:
   ```text
   --db PATH
   ```

2. Environment variable:
   ```text
   AGENT_MEMORY_DB
   ```

3. Repository-local default:
   ```text
   <project-root>/.agent-memory/memory.db
   ```

Determine `<project-root>` by:

1. attempting:
   ```text
   git rev-parse --show-toplevel
   ```
2. using the current working directory if Git is unavailable or the directory is not a repository

The resolved path must be available through a reusable configuration function.

Create parent directories when initializing or writing.

Do not automatically create or mutate a database during read-only commands unless explicitly documented.

---

# 7. Database Configuration

Every opened writable connection should apply:

```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
```

Also use:

```sql
PRAGMA synchronous = NORMAL;
```

Use transactions for writes.

Use parameterized SQL only.

Never build SQL by concatenating user-provided values.

---

# 8. Initial Schema

Place the schema in `schema.sql`.

```sql`
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO schema_metadata(key, value)
VALUES ('schema_version', '2')
ON CONFLICT(key) DO NOTHING;

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'project',
    kind TEXT NOT NULL DEFAULT 'note',

    memory_key TEXT,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',

    source_agent TEXT NOT NULL DEFAULT 'unknown',
    source_path TEXT,

    importance INTEGER NOT NULL DEFAULT 3
        CHECK (importance BETWEEN 1 AND 5),

    content_sha256 TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    last_accessed_at TEXT,
    access_count INTEGER NOT NULL DEFAULT 0,

    UNIQUE(project, scope, kind, memory_key)
);

CREATE INDEX IF NOT EXISTS idx_memories_project
    ON memories(project);

CREATE INDEX IF NOT EXISTS idx_memories_project_kind
    ON memories(project, kind);

CREATE INDEX IF NOT EXISTS idx_memories_project_importance
    ON memories(project, importance DESC);

CREATE INDEX IF NOT EXISTS idx_memories_updated
    ON memories(project, updated_at DESC);

CREATE TABLE IF NOT EXISTS mirrored_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project TEXT NOT NULL,
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,

    source_agent TEXT NOT NULL DEFAULT 'unknown',

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    UNIQUE(project, path)
);

CREATE INDEX IF NOT EXISTS idx_mirrored_files_project_path
    ON mirrored_files(project, path);
```

## Full-text search

Attempt to create an FTS5 external-content table:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    tags,
    content='memories',
    content_rowid='id'
);
```

Add synchronization triggers:

```sql
CREATE TRIGGER IF NOT EXISTS memories_after_insert
AFTER INSERT ON memories
BEGIN
    INSERT INTO memories_fts(rowid, content, tags)
    VALUES (new.id, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_after_delete
AFTER DELETE ON memories
BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags)
    VALUES ('delete', old.id, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_after_update
AFTER UPDATE ON memories
BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags)
    VALUES ('delete', old.id, old.content, old.tags);

    INSERT INTO memories_fts(rowid, content, tags)
    VALUES (new.id, new.content, new.tags);
END;
```

Some Python SQLite builds may not include FTS5.

The application must:

- detect whether FTS5 is available
- use FTS5 when available
- gracefully fall back to parameterized `LIKE` searches when unavailable
- expose the active search backend in `agent-memory status`

Do not fail initialization solely because FTS5 is unavailable.

---

# 9. Memory Model

Create a `Memory` dataclass containing at least:

```python
@dataclass(frozen=True, slots=True)
class Memory:
    id: int
    project: str
    scope: str
    kind: str
    memory_key: str | None
    content: str
    tags: tuple[str, ...]
    source_agent: str
    source_path: str | None
    importance: int
    content_sha256: str
    created_at: str
    updated_at: str
    last_accessed_at: str | None
    access_count: int
```

Also create input/result dataclasses where useful, such as:

```python
@dataclass(frozen=True, slots=True)
class MemoryInput:
    project: str
    scope: str = "project"
    kind: str = "note"
    memory_key: str | None = None
    content: str = ""
    tags: tuple[str, ...] = ()
    source_agent: str = "unknown"
    source_path: str | None = None
    importance: int = 3
```

Search results may include a relevance score.

All models used by the future MCP adapter must have an easy conversion to dictionaries.

---

# 10. Tags

For the first version, store normalized tags as a comma-separated string.

Normalization rules:

- trim whitespace
- lowercase tags
- remove empty tags
- remove duplicates
- sort tags for deterministic storage
- reject commas inside a single tag or convert them safely

Example:

```text
QueryDSL, jpa, DTO, querydsl
```

becomes:

```text
dto,jpa,querydsl
```

Keep tag parsing and serialization in reusable helper functions.

---

# 11. Stable Memory Categories

Support arbitrary kinds, but document these recommended values:

```text
architecture
decision
preference
command
workflow
bug
workaround
lesson
environment
constraint
todo
note
```

Do not hard-code these as a closed enum unless the implementation still allows custom values.

---

# 12. Service Layer Contract

Implement a reusable `MemoryService`.

Suggested public methods:

```python
class MemoryService:
    def initialize(self) -> dict: ...

    def status(self) -> dict: ...

    def put(self, memory: MemoryInput) -> Memory: ...

    def get_by_id(self, memory_id: int, *, touch: bool = True) -> Memory | None: ...

    def get_by_key(
        self,
        *,
        project: str,
        scope: str,
        kind: str,
        memory_key: str,
        touch: bool = True,
    ) -> Memory | None: ...

    def search(
        self,
        *,
        project: str,
        query: str,
        limit: int = 10,
        scope: str | None = None,
        kind: str | None = None,
        tag: str | None = None,
        min_importance: int | None = None,
        touch: bool = True,
    ) -> list[dict]: ...

    def recent(
        self,
        *,
        project: str,
        limit: int = 10,
        kind: str | None = None,
        min_importance: int | None = None,
    ) -> list[Memory]: ...

    def delete_by_id(self, memory_id: int) -> bool: ...

    def delete_by_key(
        self,
        *,
        project: str,
        scope: str,
        kind: str,
        memory_key: str,
    ) -> bool: ...

    def mirror_file(
        self,
        *,
        project: str,
        path: Path,
        source_agent: str = "unknown",
    ) -> dict: ...

    def export_markdown(
        self,
        *,
        project: str,
        output_path: Path,
        limit: int | None = None,
        min_importance: int | None = None,
    ) -> dict: ...
```

The exact signatures may be adjusted, but preserve the separation between:

- storage
- service logic
- CLI formatting

---

# 13. Put and Upsert Behavior

`put` must support two behaviors.

## Keyed memory

When `memory_key` is supplied, upsert using:

```text
project + scope + kind + memory_key
```

On conflict:

- update `content`
- update `tags`
- update `source_agent`
- update `source_path`
- update `importance`
- update `content_sha256`
- update `updated_at`
- preserve `created_at`
- preserve `access_count`
- preserve `last_accessed_at`

Return whether the result was inserted, updated, or unchanged.

If the incoming content hash and all mutable metadata are unchanged, avoid an unnecessary update.

## Unkeyed memory

When `memory_key` is absent:

- insert a new row
- do not deduplicate solely by content hash
- return the inserted row

This allows both durable keyed facts and journal-style notes.

---

# 14. Content Input Rules

For commands that accept content, support exactly one of:

```text
--content "text"
--content-file PATH
--stdin
```

Examples:

```powershell
agent-memory put `
  --project protini `
  --kind decision `
  --key querydsl-projection-style `
  --content "Prefer constructor projections for DTO query results."
```

```powershell
Get-Content .\memory-note.md -Raw |
  agent-memory put `
    --project protini `
    --kind note `
    --stdin
```

Reject calls that provide more than one content source.

Reject empty content after normalization unless an explicit future option allows it.

Preserve meaningful internal whitespace.

Normalize line endings for hashing so the same content written with CRLF or LF receives the same hash.

---

# 15. CLI Commands

Implement these commands.

## `init`

```text
agent-memory init
```

Options:

```text
--db PATH
--json
```

Behavior:

- resolve database path
- create parent directory
- initialize or upgrade schema
- report database path
- report schema version
- report FTS5 availability

Running `init` multiple times must be safe.

---

## `status`

```text
agent-memory status
```

Output should include:

- resolved database path
- whether the database exists
- schema version
- project
- total memory count
- FTS5 or LIKE search backend
- WAL mode
- most recent update timestamp

Support `--json`.

---

## `put`

```text
agent-memory put [options]
```

Required:

```text
--project PROJECT
--content TEXT | --content-file PATH | --stdin
```

Optional:

```text
--scope SCOPE
--kind KIND
--key MEMORY_KEY
--tag TAG
--tags TAG1,TAG2
--importance 1..5
--agent AGENT_NAME
--source-path PATH
--json
```

Allow repeated `--tag`.

Examples:

```powershell
agent-memory put `
  --project msfs-input-router `
  --kind architecture `
  --key target-framework `
  --content "The main application and tests target net10.0-windows." `
  --importance 5 `
  --tag dotnet `
  --tag architecture `
  --agent codex
```

Human output:

```text
Updated memory 12: architecture/target-framework
```

JSON output should include:

```json
{
  "operation": "updated",
  "memory": {
    "id": 12,
    "project": "msfs-input-router",
    "kind": "architecture",
    "memory_key": "target-framework"
  }
}
```

---

## `get`

Support either:

```text
agent-memory get --id 12
```

or:

```text
agent-memory get \
  --project protini \
  --scope project \
  --kind command \
  --key run-backend
```

Exactly one lookup mode must be used.

Support `--json`.

By default, successful retrieval updates:

- `last_accessed_at`
- `access_count`

Support:

```text
--no-touch
```

for inspection without mutating access metadata.

---

## `search`

```text
agent-memory search "QueryDSL DTO projection" --project protini
```

Options:

```text
--project PROJECT
--scope SCOPE
--kind KIND
--tag TAG
--min-importance 1..5
--limit N
--no-touch
--json
```

Default limit:

```text
10
```

Maximum limit:

```text
100
```

Human-readable results should be compact and useful to an agent.

Suggested output:

```text
[5] decision/querydsl-projection-style
Importance: 4
Updated: 2026-08-03T23:15:12.000Z
Tags: dto, jpa, querydsl

Prefer constructor projections for DTO query results.
```

Separate records with a clear delimiter.

JSON output must contain full structured records and optional relevance scores.

When FTS5 is active:

- use `MATCH`
- rank with `bm25`
- combine rank with importance in a deterministic ordering

A reasonable order is:

1. higher importance
2. better FTS rank
3. more recently updated

When the fallback backend is active:

- split the query into normalized terms
- use parameterized `LIKE`
- require all terms or use a clearly documented strategy
- order by importance and recency

Catch malformed FTS query syntax and safely retry using a quoted or tokenized query.

---

## `recent`

```text
agent-memory recent --project protini
```

Options:

```text
--project PROJECT
--kind KIND
--min-importance 1..5
--limit N
--json
```

Order by:

```text
updated_at DESC
```

---

## `delete`

Support:

```text
agent-memory delete --id 12
```

or keyed deletion:

```text
agent-memory delete \
  --project protini \
  --scope project \
  --kind command \
  --key run-backend
```

Require confirmation for an interactive human terminal unless:

```text
--yes
```

is supplied.

An AI agent should use `--yes`.

Support `--json`.

Deleting a missing record should produce a clear result and a nonzero exit code suitable for scripts.

---

## `mirror-file`

```text
agent-memory mirror-file PATH --project protini
```

Options:

```text
--project PROJECT
--agent AGENT_NAME
--json
```

Behavior:

- read the complete file as UTF-8
- compute a normalized SHA-256 hash
- keep one current row per `(project, path)`; insert on first mirror, update when content changes, and leave it unchanged when the hash matches
- report `inserted`, `updated`, or `unchanged`
- store the path relative to the project root when possible
- do not automatically turn every Markdown section into a semantic memory

This command is for the current exact document content, not semantic memory extraction. Git can retain revision history. Schema version 2 migrates version 1 mirrors by keeping the highest-ID row per path after backing up the old database. Legacy JSON snapshots with multiple revisions per path import the highest-ID revision. The older format cannot identify an A → B → A return to A, because version 1 did not record the last mirrored state.

## `import-json` mirrored Markdown restore

The CLI imports snapshot rows into SQLite and restores mirrored `.md` files relative to the detected project root. Create missing files without prompting. Leave existing files untouched when their normalized UTF-8 content matches the snapshot. For differing files, ask the user before overwriting in an interactive terminal. In a noninteractive run, leave differing files in place and report conflicts; `--overwrite-files` explicitly permits replacement. `--no-restore-files` performs database-only import. `--dry-run` does not write files or prompt.

Never restore an absolute path, a path with `..`, a path through a symlink outside the project root, or a path inside `.git` or `.agent-memory`. Snapshot verification and other service callers that do not supply a restore root remain database-only. The JSON result reports file actions, conflicts, and failures separately from database row counts.

Do not scan arbitrary directories in the first version.

---

## `export-md`

```text
agent-memory export-md \
  --project protini \
  --output .agent-memory/MEMORY.generated.md
```

Options:

```text
--project PROJECT
--output PATH
--limit N
--min-importance 1..5
--json
```

The generated file must begin with:

```markdown
<!-- GENERATED FILE. DO NOT EDIT DIRECTLY. -->
<!-- Source: .agent-memory/memory.db -->
```

Suggested organization:

```markdown
# Agent Memory: protini

Generated: 2026-08-03T23:20:00Z

## Architecture

### target-framework

- Importance: 5
- Scope: project
- Updated: 2026-08-03T23:15:12Z
- Tags: dotnet, architecture

The main application and tests target `net10.0-windows`.
```

Group by `kind`.

Within a group, order by:

1. importance descending
2. updated time descending
3. memory key or ID

Use a safe fallback title for unkeyed memories.

Write the file atomically:

1. write a temporary sibling file
2. flush and close it
3. replace the final output path

---

# 16. JSON Output Contract

Every command that supports `--json` must:

- write one valid JSON object to stdout
- write diagnostics only to stderr
- avoid decorative text
- use stable field names
- use UTF-8
- return timestamps as ISO 8601 strings
- return tags as JSON arrays

Successful output example:

```json
{
  "ok": true,
  "operation": "inserted",
  "database": "C:\\Development\\protini\\.agent-memory\\memory.db",
  "memory": {
    "id": 17,
    "project": "protini",
    "scope": "project",
    "kind": "decision",
    "memory_key": "querydsl-projection-style",
    "content": "Prefer constructor projections for DTO query results.",
    "tags": [
      "dto",
      "jpa",
      "querydsl"
    ],
    "source_agent": "codex",
    "source_path": null,
    "importance": 4,
    "created_at": "2026-08-03T23:15:12.000Z",
    "updated_at": "2026-08-03T23:15:12.000Z"
  }
}
```

Error output to stdout when `--json` is active:

```json
{
  "ok": false,
  "error": {
    "code": "MEMORY_NOT_FOUND",
    "message": "No memory matched the supplied key."
  }
}
```

Also return a nonzero process exit code.

---

# 17. Exit Codes

Define and document stable exit codes.

Suggested values:

```text
0  success
1  general error
2  invalid command-line usage
3  database or schema error
4  memory not found
5  invalid content or validation error
6  file read or write error
```

Do not expose raw Python tracebacks during normal CLI use.

A `--debug` option may expose tracebacks for development.

---

# 18. Error Handling

Create application-specific exceptions, for example:

```python
class AgentMemoryError(Exception):
    code: str = "AGENT_MEMORY_ERROR"

class ValidationError(AgentMemoryError):
    code = "VALIDATION_ERROR"

class MemoryNotFoundError(AgentMemoryError):
    code = "MEMORY_NOT_FOUND"

class DatabaseError(AgentMemoryError):
    code = "DATABASE_ERROR"
```

Map exceptions to:

- concise human messages
- stable JSON error objects
- documented exit codes

Preserve the original exception as the cause where useful.

---

# 19. MCP-Ready Architecture

Do not implement a full MCP server in the initial release unless it can be added without compromising the CLI.

Prepare for these future MCP tools:

```text
memory_status
memory_put
memory_get
memory_search
memory_recent
memory_delete
memory_mirror_file
memory_export_markdown
```

The future MCP adapter should look conceptually like:

```python
from agent_memory.service import MemoryService
from agent_memory.models import MemoryInput

service = MemoryService(...)

def memory_put(arguments: dict) -> dict:
    memory_input = MemoryInput.from_dict(arguments)
    result = service.put(memory_input)
    return result.to_dict()
```

The future server must not:

- shell out to the CLI
- parse human-readable CLI output
- duplicate SQL
- duplicate validation rules
- maintain a second data model

## Optional placeholder

It is acceptable to add:

```text
src/agent_memory/mcp_server.py
```

with documentation and a clear `NotImplementedError`, but do not make the normal CLI import an optional MCP package.

A future packaging section may use:

```toml
[project.optional-dependencies]
mcp = ["mcp>=1,<2"]
```

Do not require this optional dependency for CLI users.

---

# 20. Agent Bootstrap Instructions

Create reusable snippets in `examples/`.

## `examples/AGENTS-memory-section.md`

```markdown
## Persistent project memory

Durable project memory is stored in `.agent-memory/memory.db`.

Before beginning substantial work:

1. Search memory for the current task, relevant subsystem, known problems, and prior decisions.
2. Load only the most relevant results.
3. Treat current repository files and explicit user instructions as higher priority than stored memory.

Useful commands:

```text
agent-memory status --json
agent-memory search "<task topic>" --project "<project>" --limit 8 --json
agent-memory recent --project "<project>" --limit 5 --json
```

Before finishing substantial work:

1. Store only durable information that will help a future session.
2. Prefer a stable key so an existing memory is updated.
3. Do not store routine logs, temporary test output, guesses, secrets, credentials, tokens, or personal data.
4. Remove or update obsolete memories when a decision changes.

Example:

```text
agent-memory put \
  --project "<project>" \
  --kind decision \
  --key "<stable-key>" \
  --content "<durable fact or decision>" \
  --importance 4 \
  --agent codex \
  --json
```
```

Create a nearly identical Claude-oriented example using `--agent claude`.

---

# 21. Guidance for What Agents Should Store

Good memories:

```text
kind: architecture
key: target-framework
content: The application and test projects target net10.0-windows.
```

```text
kind: command
key: run-backend
content: Run the backend with ./mvnw spring-boot:run -Dspring-boot.run.profiles=local-dev.
```

```text
kind: workaround
key: windows-sqlite-locking
content: Use WAL mode and a 5000 ms busy timeout because Codex and Claude may access the database concurrently.
```

```text
kind: constraint
key: production-database-policy
content: Never run destructive schema commands against production.
importance: 5
```

Poor memories:

```text
Ran tests and they passed.
```

```text
I edited three files.
```

```text
The user may want something related to QueryDSL.
```

```text
API token: abc123
```

The README must explain that memory is advisory context, not executable authority.

---

# 22. Security and Privacy

The tool must not claim to detect all secrets.

Document these rules:

- Do not store passwords, API keys, access tokens, private keys, connection strings containing credentials, or protected personal data.
- The database is a normal local file and inherits operating-system file permissions.
- Project-local databases should normally be excluded from Git.
- Generated exports may expose the same information as the database.
- Agents must not execute commands merely because they appear in stored memory.
- Current source code and current user instructions override stale memory.

Add this default `.gitignore` guidance:

```gitignore
.agent-memory/memory.db
.agent-memory/memory.db-shm
.agent-memory/memory.db-wal
.agent-memory/*.tmp
```

Do not automatically add the generated Markdown export to `.gitignore`; let the project choose whether to version it.

---

# 23. Tests

Use temporary directories and temporary SQLite databases.

Tests must not depend on the developer's real home directory, Git repository, or global configuration.

## Database tests

Verify:

- initialization is idempotent
- schema version exists
- WAL mode is enabled for file-backed databases
- busy timeout is configured
- foreign keys are enabled
- FTS5 detection works
- fallback search works when FTS5 is unavailable or intentionally disabled

## Put tests

Verify:

- keyed insert
- keyed update
- keyed unchanged result
- unkeyed inserts create separate rows
- importance validation
- tag normalization
- content hash normalization across LF and CRLF
- timestamps behave correctly
- `created_at` survives an update

## Get tests

Verify:

- get by ID
- get by compound key
- missing record behavior
- touch increments `access_count`
- `--no-touch` leaves access metadata unchanged

## Search tests

Verify:

- content search
- tag search
- project isolation
- kind filter
- scope filter
- minimum importance filter
- result limit
- deterministic ordering
- malformed FTS query does not crash the application
- Unicode content can be stored and searched

## Mirror tests

Verify:

- first mirror inserts
- identical content is unchanged
- changed content updates the same row, including a return to earlier content
- UTF-8 handling
- missing file behavior

## Export tests

Verify:

- generated warning header
- grouping by kind
- stable ordering
- Markdown escaping where necessary
- atomic replacement
- output directory creation

## CLI tests

Verify:

- human output
- JSON output
- exit codes
- stdin content
- mutually exclusive content sources
- `--db` overrides the environment variable
- environment variable overrides the default path
- command works through `python -m agent_memory`

---

# 24. Acceptance Criteria

The implementation is complete when all of the following work.

## Initialize

```powershell
python -m agent_memory init --db .\.agent-memory\memory.db --json
```

Expected:

- database is created
- schema version is reported
- FTS status is reported
- command exits with code 0

## Store a keyed memory

```powershell
python -m agent_memory put `
  --db .\.agent-memory\memory.db `
  --project demo `
  --kind decision `
  --key database-choice `
  --content "Use SQLite as the canonical agent memory store." `
  --tag sqlite `
  --tag architecture `
  --importance 5 `
  --agent codex `
  --json
```

Expected:

- one row is inserted
- JSON is valid
- tags are normalized
- operation is `inserted`

## Update the same memory

```powershell
python -m agent_memory put `
  --db .\.agent-memory\memory.db `
  --project demo `
  --kind decision `
  --key database-choice `
  --content "Use SQLite as the canonical store and generate Markdown only for inspection." `
  --tag sqlite `
  --tag architecture `
  --importance 5 `
  --agent claude `
  --json
```

Expected:

- the same row is updated
- no duplicate keyed row is created
- operation is `updated`
- `created_at` is unchanged
- `updated_at` changes

## Search

```powershell
python -m agent_memory search "canonical SQLite" `
  --db .\.agent-memory\memory.db `
  --project demo `
  --limit 5 `
  --json
```

Expected:

- the stored memory is returned
- output is valid JSON
- result includes relevance data when FTS5 is active

## Mirror a Markdown file

```powershell
python -m agent_memory mirror-file .\AGENTS.md `
  --db .\.agent-memory\memory.db `
  --project demo `
  --agent codex `
  --json
```

Expected:

- first call reports `inserted`
- second unchanged call reports `unchanged`

## Export Markdown

```powershell
python -m agent_memory export-md `
  --db .\.agent-memory\memory.db `
  --project demo `
  --output .\.agent-memory\MEMORY.generated.md `
  --json
```

Expected:

- file is created
- generated-file warning is present
- stored decision appears under a `Decision` or `Decisions` heading

## Test suite

```text
pytest
```

Expected:

- all tests pass on Windows
- no tests write to the real user profile or repository database

---

# 25. README Requirements

The README should include:

1. what the tool does
2. why SQLite is used
3. installation
4. quick start
5. command reference
6. agent bootstrap examples
7. JSON examples
8. database path resolution
9. FTS5 fallback behavior
10. Markdown mirroring versus semantic memory
11. security cautions
12. MCP migration design
13. development and testing commands

Include examples for both PowerShell and POSIX shells where syntax differs.

---

# 26. Implementation Sequence

Implement in this order:

1. packaging and module entry point
2. path resolution
3. schema initialization
4. models and serialization
5. service-layer `put`, `get`, and `recent`
6. FTS5 detection and search fallback
7. search filters and ranking
8. CLI human output
9. CLI JSON output and stable errors
10. current mirrored files
11. Markdown export
12. tests
13. README and agent bootstrap examples
14. final cleanup and type annotations

Commit-quality code is expected.

---

# 27. Non-Goals for Version 1

Do not add these unless required to satisfy the acceptance criteria:

- vector embeddings
- semantic embedding search
- remote database access
- HTTP APIs
- background daemons
- automatic directory watching
- automatic AI summarization
- automatic secret scanning
- encryption at rest
- cloud synchronization
- multi-user authentication
- a graphical interface
- a full MCP server
- an ORM
- database migration frameworks

The design should allow these later without making the initial CLI heavy.

---

# 28. Future MCP Phase

After the CLI is stable, create an optional MCP adapter.

The MCP phase should:

1. add the official Python MCP package as an optional dependency
2. instantiate the existing `MemoryService`
3. expose service methods as MCP tools
4. use the same path-resolution rules
5. return structured JSON-safe data
6. reuse all validation and exceptions
7. add adapter tests without duplicating service tests

A future MCP tool definition might conceptually accept:

```json
{
  "project": "protini",
  "scope": "project",
  "kind": "decision",
  "memory_key": "querydsl-projection-style",
  "content": "Prefer constructor projections for DTO query results.",
  "tags": [
    "querydsl",
    "jpa",
    "dto"
  ],
  "importance": 4,
  "source_agent": "codex"
}
```

The MCP adapter should remain small because the CLI and MCP layers are two doors into the same memory engine.

---

# 29. Final Deliverables

Produce:

```text
pyproject.toml
README.md
LICENSE
.gitignore
src/agent_memory/__init__.py
src/agent_memory/__main__.py
src/agent_memory/cli.py
src/agent_memory/config.py
src/agent_memory/database.py
src/agent_memory/models.py
src/agent_memory/service.py
src/agent_memory/markdown.py
src/agent_memory/schema.sql
tests/*
examples/AGENTS-memory-section.md
examples/CLAUDE-memory-section.md
```

Also provide a concise final implementation report containing:

- files created
- design decisions
- commands tested
- test results
- known limitations
- exact next step for adding MCP

Do not stop after creating scaffolding. Implement the working CLI, run the tests, and fix failures before reporting completion.
