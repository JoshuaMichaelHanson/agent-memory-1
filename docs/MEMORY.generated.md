<!-- GENERATED FILE. DO NOT EDIT DIRECTLY. -->
<!-- Source: C:\Development\agent-memory-1\.agent-memory\memory.db -->

# Agent Memory: agent-memory-1

Generated: 2026-08-04T23:04:19Z

## Architecture

### cli-service-separation

- ID: 3
- Importance: 5
- Scope: project
- Updated: 2026-08-04T23:04:18.293Z
- Tags: cli, mcp, service

The CLI remains a thin adapter over reusable service/database logic so a future MCP server can call MemoryService directly without shelling out or duplicating SQL.

## Command

### run-tests

- ID: 5
- Importance: 5
- Scope: project
- Updated: 2026-08-04T23:04:18.609Z
- Tags: pytest, venv, windows

Run the full test suite with .\.venv\Scripts\python.exe -m pytest from C:\Development\agent-memory-1. The current Windows checkout reports a non-failing pytest cache warning.

## Constraint

### local-db-gitignore

- ID: 6
- Importance: 4
- Scope: project
- Updated: 2026-08-04T23:04:18.768Z
- Tags: gitignore, privacy, sqlite

Do not commit the live .agent-memory SQLite database files. Git ignores memory.db, memory.db-shm, memory.db-wal, and .agent-memory/*.tmp; share memory through tracked JSON and Markdown exports instead.

## Decision

### sqlite-canonical-store

- ID: 2
- Importance: 5
- Scope: project
- Updated: 2026-08-04T23:04:18.136Z
- Tags: architecture, memory, sqlite

SQLite is the canonical memory store for agent-memory. Markdown files are bootstrap context, optional generated exports, or compatibility artifacts.

## Environment

### project-state

- ID: 1
- Importance: 4
- Scope: project
- Updated: 2026-08-04T23:04:17.974Z
- Tags: bootstrap, intellij, repo

Repository path is C:\Development\agent-memory-1. Git is initialized. IntelliJ MCP is configured in .codex/config.toml and resolved the project as module agent-memory-1.

## Workflow

### memory-sync-before-checkin

- ID: 7
- Importance: 5
- Scope: project
- Updated: 2026-08-04T23:04:18.926Z
- Tags: export, git, snapshot

Before checkin after memory changes, run export-json to docs/agent-memory.snapshot.json and export-md to docs/MEMORY.generated.md. The JSON snapshot recreates local SQLite memory on another computer; the Markdown export is for human review.

### bootstrap-docs-before-db

- ID: 4
- Importance: 4
- Scope: project
- Updated: 2026-08-04T23:04:18.453Z
- Tags: bootstrap, docs

Before the SQLite database is available, use WORKING_MEMORY.md and docs/BACKLOG.md as temporary durable context. After Phase 8 cutover, write durable memory to SQLite first and keep WORKING_MEMORY.md as legacy fallback only.
