# Backlog

Use this file as the operational checklist until the SQLite memory database is available.

## Phase 0: Bootstrap Project Control

- [x] Initialize Git repository.
- [x] Add generic `.gitignore`.
- [x] Add `.agent-memory` database ignores.
- [x] Add `AGENTS.md` bootstrap instructions.
- [x] Add implementation planning docs.
- [x] Add temporary `WORKING_MEMORY.md`.

## Phase 1: Packaging and CLI Skeleton

- [x] Create `pyproject.toml` with Python 3.11+ metadata and `agent-memory` console script.
- [x] Create `src/agent_memory/__init__.py`.
- [x] Create `src/agent_memory/__main__.py`.
- [x] Create initial `src/agent_memory/cli.py` using `argparse`.
- [x] Add a top-level `README.md` skeleton.
- [x] Add a minimal CLI smoke test.
- [x] Verify `python -m agent_memory --help`.
- [x] Add venv-based development setup documentation and scripts.

## Phase 2: Configuration and Database Initialization

- [x] Implement `src/agent_memory/config.py`.
- [x] Resolve DB path in this order: `--db`, `AGENT_MEMORY_DB`, project-local default.
- [x] Detect Git root with `git rev-parse --show-toplevel`, falling back to current directory.
- [x] Implement `src/agent_memory/database.py`.
- [x] Add `src/agent_memory/schema.sql`.
- [x] Apply WAL, busy timeout, foreign keys, and synchronous NORMAL on writable connections.
- [x] Detect FTS5 availability without failing initialization if unavailable.
- [x] Implement `init`.
- [x] Implement `status`.
- [x] Add database initialization and status tests.

## Phase 3: Models, Validation, and Put

- [x] Implement `Memory` dataclass.
- [x] Implement `MemoryInput` dataclass.
- [x] Add dictionary serialization helpers.
- [x] Implement tag normalization and serialization.
- [x] Implement content normalization for hashing.
- [x] Implement service exceptions and stable error codes.
- [x] Implement `MemoryService.put`.
- [x] Implement `put` CLI command.
- [x] Validate exactly one content source: `--content`, `--content-file`, or `--stdin`.
- [x] Add keyed insert, keyed update, unchanged, unkeyed insert, tag, hash, and validation tests.

## Phase 4: Get and Recent

- [x] Implement `MemoryService.get_by_id`.
- [x] Implement `MemoryService.get_by_key`.
- [x] Implement touch behavior for retrieval.
- [x] Implement `MemoryService.recent`.
- [x] Implement `get` CLI command.
- [x] Implement `recent` CLI command.
- [x] Add retrieval, touch, no-touch, missing, and recent ordering tests.

## Phase 5: Search

- [x] Create FTS5 virtual table and triggers when FTS5 is available.
- [x] Implement FTS search with `MATCH` and deterministic ordering.
- [x] Implement safe retry for malformed FTS queries.
- [x] Implement parameterized `LIKE` fallback.
- [x] Implement project, scope, kind, tag, minimum importance, and limit filters.
- [x] Implement `search` CLI command.
- [x] Add search tests for content, tags, filters, ordering, fallback, malformed syntax, and Unicode.

## Phase 6: Delete, Mirror, and Export

- [x] Implement delete by ID.
- [x] Implement delete by compound key.
- [x] Implement interactive confirmation and `--yes`.
- [x] Implement `mirror_file`.
- [x] Implement `export_markdown`.
- [x] Write Markdown output atomically.
- [x] Implement `delete`, `mirror-file`, and `export-md` CLI commands.
- [x] Add delete, mirror, and export tests.

## Phase 7: Documentation and Final Readiness

- [x] Expand README with installation, quick start, command reference, JSON examples, path resolution, FTS fallback, security cautions, and MCP migration design.
- [x] Add `examples/AGENTS-memory-section.md`.
- [x] Add `examples/CLAUDE-memory-section.md`.
- [x] Run full `pytest`.
- [x] Run acceptance commands from the implementation spec.
- [x] Write final implementation report.

## Phase 8: Self-Hosting Memory Cutover

- [x] Initialize `.agent-memory/memory.db`.
- [x] Insert project state memory with key `project-state`.
- [x] Insert architecture decision with key `sqlite-canonical-store`.
- [x] Insert workflow memory with key `bootstrap-docs-before-db`.
- [x] Insert command memory with key `run-tests`.
- [x] Search inserted memories to verify retrieval.
- [x] Update `AGENTS.md` to prefer `agent-memory search` before reading `WORKING_MEMORY.md`.
- [x] Keep `WORKING_MEMORY.md` only as a legacy bootstrap note or generated export companion.
- [x] Document JSON snapshot export before checkin and restore on another computer.
