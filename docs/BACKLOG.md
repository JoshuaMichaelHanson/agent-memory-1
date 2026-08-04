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

- [ ] Implement `MemoryService.get_by_id`.
- [ ] Implement `MemoryService.get_by_key`.
- [ ] Implement touch behavior for retrieval.
- [ ] Implement `MemoryService.recent`.
- [ ] Implement `get` CLI command.
- [ ] Implement `recent` CLI command.
- [ ] Add retrieval, touch, no-touch, missing, and recent ordering tests.

## Phase 5: Search

- [ ] Create FTS5 virtual table and triggers when FTS5 is available.
- [ ] Implement FTS search with `MATCH` and deterministic ordering.
- [ ] Implement safe retry for malformed FTS queries.
- [ ] Implement parameterized `LIKE` fallback.
- [ ] Implement project, scope, kind, tag, minimum importance, and limit filters.
- [ ] Implement `search` CLI command.
- [ ] Add search tests for content, tags, filters, ordering, fallback, malformed syntax, and Unicode.

## Phase 6: Delete, Mirror, and Export

- [ ] Implement delete by ID.
- [ ] Implement delete by compound key.
- [ ] Implement interactive confirmation and `--yes`.
- [ ] Implement `mirror_file`.
- [ ] Implement `export_markdown`.
- [ ] Write Markdown output atomically.
- [ ] Implement `delete`, `mirror-file`, and `export-md` CLI commands.
- [ ] Add delete, mirror, and export tests.

## Phase 7: Documentation and Final Readiness

- [ ] Expand README with installation, quick start, command reference, JSON examples, path resolution, FTS fallback, security cautions, and MCP migration design.
- [ ] Add `examples/AGENTS-memory-section.md`.
- [ ] Add `examples/CLAUDE-memory-section.md`.
- [ ] Run full `pytest`.
- [ ] Run acceptance commands from the implementation spec.
- [ ] Write final implementation report.

## Phase 8: Self-Hosting Memory Cutover

- [ ] Initialize `.agent-memory/memory.db`.
- [ ] Insert project state memory with key `project-state`.
- [ ] Insert architecture decision with key `sqlite-canonical-store`.
- [ ] Insert workflow memory with key `bootstrap-docs-before-db`.
- [ ] Insert command memory with key `run-tests`.
- [ ] Search inserted memories to verify retrieval.
- [ ] Update `AGENTS.md` to prefer `agent-memory search` before reading `WORKING_MEMORY.md`.
- [ ] Keep `WORKING_MEMORY.md` only as a legacy bootstrap note or generated export companion.
