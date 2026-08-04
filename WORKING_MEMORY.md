# Working Memory

This file is temporary project memory until `agent-memory` can store and search its own SQLite database.

## Current State

- Repository path: `C:\Development\agent-memory-1`.
- Active branch for current work: `feat/phase-1`.
- Git repository has been initialized.
- `.gitignore` ignores IntelliJ, VS Code, Python, JavaScript, Java/JVM, build outputs, and local `.agent-memory` SQLite database files.
- IntelliJ MCP is configured through `.codex/config.toml` using `http://127.0.0.1:64342/stream`.
- The live IntelliJ MCP server resolved this project and reported one Java module named `agent-memory-1`.
- The full implementation spec is in `codex-sqlite-agent-memory-implementation-spec.md`.
- Phase 1 is complete: `pyproject.toml`, `README.md`, `LICENSE`, `src/agent_memory`, and smoke tests exist.
- The Phase 1 CLI supports `--help` and a limited `status --json --db <path>` command. Other commands are placeholders until later phases.
- Because the project uses a `src` layout and is not installed in the environment, local module execution currently uses `PYTHONPATH=src`.
- `.venv` can be created with `scripts/setup-dev.ps1`; it installs the project editable with `.[dev]` and pytest. The setup script passed with pytest 9.1.1 on Python 3.14.3 after running outside the sandbox because ensurepip/pip temp-file writes were blocked inside the sandbox.

## Durable Decisions

- Implement the first release as a Python 3.11+ CLI named `agent-memory`.
- Keep runtime dependencies to the Python standard library for version 1.
- Use SQLite as the canonical memory store.
- Keep CLI parsing and output formatting separate from reusable service/database logic.
- Prepare for MCP by making `MemoryService` methods accept normal Python values and return dataclasses or JSON-serializable dictionaries.
- Do not implement the MCP server in version 1.
- Use Markdown files only as bootstrap context and optional generated exports, not as canonical memory after the SQLite database is working.
- Keep tests away from the real user profile and real project database. Current smoke tests use ignored paths under `tmp/tests`.

## Next Task

Start Phase 2 in `docs/BACKLOG.md`: implement configuration, database connection handling, `schema.sql`, idempotent `init`, and richer `status`.

## Migration Target

When `python -m agent_memory init`, keyed `put`, and `search` pass locally, migrate this file's durable facts into `.agent-memory/memory.db` using stable keys.
