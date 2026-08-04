# Implementation Plan

Build `agent-memory` in small, testable phases. Each phase should leave the repository in a usable state and update `WORKING_MEMORY.md` until SQLite memory becomes canonical.

## Phase 0: Bootstrap Project Control

Goal: make the repository navigable for future agents.

Deliverables:

- Git repository initialized.
- Generic `.gitignore` in place.
- `AGENTS.md` bootstrap instructions.
- Planning docs in `docs/`.
- Temporary `WORKING_MEMORY.md`.

Status: complete.

## Phase 1: Packaging and CLI Skeleton

Goal: make `python -m agent_memory` and the future `agent-memory` console script reachable.

Deliverables:

- `pyproject.toml`
- `src/agent_memory/__init__.py`
- `src/agent_memory/__main__.py`
- `src/agent_memory/cli.py`
- initial `README.md`
- basic tests that invoke the module

Acceptance:

- `python -m agent_memory --help` exits 0.
- `python -m agent_memory status --json --db <tmp>` returns valid JSON even before initialization.

## Phase 2: Configuration and Database Initialization

Goal: create the database safely and report status.

Deliverables:

- `config.py` path resolution
- `database.py` connection handling and schema initialization
- `schema.sql`
- `init` command
- `status` command

Acceptance:

- `python -m agent_memory init --db .\.agent-memory\memory.db --json` creates the database.
- Re-running `init` is idempotent.
- `status --json` reports path, existence, schema version, WAL mode, total count, and search backend.

## Phase 3: Models, Validation, and Core Memory Writes

Goal: support durable keyed and unkeyed memory.

Deliverables:

- `models.py` dataclasses
- tag normalization helpers
- content hash normalization
- service exceptions and exit code mapping
- `MemoryService.put`
- `put` CLI command

Acceptance:

- Keyed insert returns `inserted`.
- Repeating unchanged keyed input returns `unchanged`.
- Changing keyed input returns `updated` without duplicating the row.
- Unkeyed puts create separate rows.
- JSON output is stable and machine-readable.

## Phase 4: Retrieval and Recent Memory

Goal: retrieve useful records without search.

Deliverables:

- `MemoryService.get_by_id`
- `MemoryService.get_by_key`
- `MemoryService.recent`
- `get` CLI command
- `recent` CLI command

Acceptance:

- `get --id` and keyed `get` work.
- Touch behavior increments `access_count` by default.
- `--no-touch` leaves access metadata unchanged.
- `recent` orders by `updated_at DESC`.

## Phase 5: Search

Goal: provide relevant context retrieval.

Deliverables:

- FTS5 detection
- FTS external-content table and triggers
- FTS-backed search
- parameterized `LIKE` fallback
- search filters and deterministic ordering
- `search` CLI command

Acceptance:

- Search finds stored content and tags.
- Project, kind, scope, tag, importance, and limit filters work.
- Malformed FTS syntax does not crash.
- `status` reports whether FTS5 or `LIKE` is active.

## Phase 6: Delete, Mirror, and Export

Goal: complete the version 1 behavioral surface.

Deliverables:

- `delete` command with `--yes`
- `mirror-file` command
- `markdown.py`
- `export-md` command with atomic writes

Acceptance:

- Missing deletes return a nonzero memory-not-found exit code.
- Repeated `mirror-file` on unchanged content returns `unchanged`.
- Changed mirrored content creates a new revision.
- Generated Markdown starts with the required warning header.

## Phase 7: Test Coverage and Documentation

Goal: make the CLI reliable enough to use as project memory.

Deliverables:

- full pytest suite from the implementation spec
- expanded README
- `examples/AGENTS-memory-section.md`
- `examples/CLAUDE-memory-section.md`
- final implementation report

Acceptance:

- `pytest` passes on Windows.
- Acceptance commands in the spec pass.
- README documents security cautions, path resolution, JSON behavior, FTS fallback, and MCP migration.

## Phase 8: Self-Hosting Memory Cutover

Goal: this project starts using its own SQLite memory database.

Deliverables:

- `.agent-memory/memory.db` initialized locally
- durable facts from `WORKING_MEMORY.md` inserted with stable keys
- `AGENTS.md` updated to search memory first
- generated Markdown export created for human review if useful

Acceptance:

- `agent-memory status --project agent-memory-1 --json` works.
- `agent-memory search "implementation plan" --project agent-memory-1 --json` returns relevant seeded memory.
- Future durable memory writes go to SQLite first, not `WORKING_MEMORY.md`.
