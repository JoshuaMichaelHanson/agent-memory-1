<!-- GENERATED FILE. DO NOT EDIT DIRECTLY. -->
<!-- Source: .agent-memory/memory.db -->

# Agent Memory: agent-memory-1

Generated: 2026-08-06T20:07:54Z

## Architecture

### agent-onboarding-instructions

- ID: 13
- Importance: 5
- Scope: project
- Updated: 2026-08-05T07:09:25.380Z
- Tags: agents, cli, onboarding, phase-13

Phase 13 is complete. The CLI now exposes agent onboarding through agent-memory instructions, machine-readable instructions JSON, and install-instructions for idempotent managed sections in AGENTS.md or another agent instruction file. The generated section tells agents to use agent-memory --help and agent-memory <command> --help, and to tell users those help commands exist instead of guessing syntax. This bridges global CLI installs until future MCP support can advertise tools, resources, and prompts directly.

### backup-restore-polish

- ID: 12
- Importance: 5
- Scope: project
- Updated: 2026-08-05T05:24:30.839Z
- Tags: phase-12, restore, snapshot

Phase 12 is complete. import-json supports --dry-run, snapshot validation reports all detected item-level problems before mutation, export-json supports --verify by restoring the written snapshot into a temporary SQLite database, and import validation warns when unkeyed memories are present because repeated real imports create new rows.

### snapshot-mirrored-files

- ID: 11
- Importance: 5
- Scope: project
- Updated: 2026-08-05T04:12:22.005Z
- Tags: mirror-file, phase-11, snapshot

Phase 11 is complete. JSON snapshots now include both semantic memories and mirrored file revisions. export-json writes mirrored_files, and import-json restores mirrored revisions idempotently by project, path, and content_sha256 while preserving keyed memory idempotence. The project snapshot now includes a mirrored AGENTS.md revision.

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
- Updated: 2026-08-06T20:04:41.729Z
- Tags: pytest, venv, windows

Run the full test suite with .\.venv\Scripts\python.exe -m pytest from the repository root. The current Windows checkout reports a non-failing pytest cache warning.

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

## Diagnostic

### doctor-command

- ID: 10
- Importance: 5
- Scope: project
- Updated: 2026-08-05T03:53:17.137Z
- Tags: diagnostics, doctor, phase-10

Phase 10 is complete. The CLI includes agent-memory doctor, which reports ok for command execution separately from healthy setup status. Doctor checks path resolution, parent write access, database existence, schema version, WAL mode, search backend, read-only inspection, live database ignore policy, tracked JSON and Markdown exports, and JSON snapshot restore into an ignored temporary database under tmp.

## Environment

### project-state

- ID: 1
- Importance: 4
- Scope: project
- Updated: 2026-08-06T20:04:41.740Z
- Tags: bootstrap, intellij, repo

Git is initialized for this checkout. IntelliJ MCP was used for early local development, and future agents should prefer current repository files plus SQLite memory over stale bootstrap notes.

## Security

### secret-guardrails

- ID: 9
- Importance: 5
- Scope: project
- Updated: 2026-08-05T02:44:35.926Z
- Tags: phase-9, production-readiness, security

Phase 9 is complete. The service layer enforces best-effort secret guardrails for put, mirror-file, and import-json before database mutation. The CLI exposes an explicit allow-sensitive override for intentional local-only storage. Detection covers obvious private key blocks, credentialed URLs, bearer token headers, secret-like assignments, AWS access key IDs, and GitHub token shapes, but remains best-effort and does not replace review.

## Workflow

### github-first-checkin-cleanup

- ID: 17
- Importance: 5
- Scope: project
- Updated: 2026-08-06T20:04:41.734Z
- Tags: cleanup, github, release

Before the first GitHub share, keep dist artifacts out of Git, document GitHub-first pipx installs, remove machine-specific paths from tracked docs and memory exports, run pytest, run agent-memory doctor, and verify JSON snapshot restore.

### phase-16-agent-skill-templates

- ID: 16
- Importance: 5
- Scope: project
- Updated: 2026-08-05T19:20:17.305Z
- Tags: agents, phase-16, skills

Phase 16 added reusable Codex and Claude skill templates for agent-memory. Codex template lives at examples/codex-skill-template/agent-memory/SKILL.md with agents/openai.yaml metadata. Claude template lives at examples/claude-skill-template/agent-memory/SKILL.md. docs/AGENT_MEMORY_SKILL_TEMPLATES.md documents install paths, expected workflow, safety rules, and test prompts. Templates teach command discovery, status/restore/search, keyed memory writes, mirror-file, copy, doctor, export-json --verify, and export-md.

### phase-15-cross-project-memory

- ID: 15
- Importance: 5
- Scope: project
- Updated: 2026-08-05T13:41:26.224Z
- Tags: cross-project, global-memory, phase-15

Phase 15 added explicit cross-project/global memory sharing. The CLI now has agent-memory copy for copying one selected memory by ID or keyed source lookup into another project in the same database, requiring --to-key for unkeyed sources. docs/CROSS_PROJECT_MEMORY.md documents project-local DB default, reusable project names, global DB advanced mode, explicit search workflow, copy promotion, snapshot sharing, and privacy/context-bleed risks.

### phase-14-production-usage-guide

- ID: 14
- Importance: 5
- Scope: project
- Updated: 2026-08-05T09:41:53.330Z
- Tags: documentation, phase-14, production-usage

Phase 14 completed production usage guidance in docs/PRODUCTION_USAGE.md. The guide recommends global CLI plus project-local database, advisory-only memory, reviewed tracked exports, explicit Markdown mirroring, production-safe examples, review-before-checkin workflow, and a temporary Developer Only Testing section for local pipx wheel installs, Windows-to-macOS testing, Python version selection, and FTS5 verification.

### production-readiness-roadmap

- ID: 8
- Importance: 5
- Scope: project
- Updated: 2026-08-05T06:06:27.872Z
- Tags: production-readiness, roadmap, workflow

Production readiness work after Phase 12 should proceed in this order: Phase 13 agent onboarding instructions, Phase 14 production usage guide, Phase 15 cross-project/global memory sharing, Phase 16 Codex and Claude skill templates, Phase 17 schema migration framework after real usage identifies needed schema changes, and Phase 18 CI/release validation last because GitHub/sharing is not yet the immediate goal. MCP remains optional future-state for personal development.

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
