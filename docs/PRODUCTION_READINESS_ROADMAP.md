# Production Readiness Roadmap

This roadmap captures the next work after Phase 8 self-hosting. MCP remains a future-state personal-development option, not a prerequisite for using the CLI.

## Readiness Position

`agent-memory` is ready for personal dogfooding and cautious use on non-sensitive projects. Before using it broadly on real production application development repositories, harden the CLI in the order below.

## Ordered Next Steps

### Phase 9: Secret Guardrails

Phase 9 status: complete. See `docs/SECRET_GUARDRAILS.md`.

Add best-effort protection against accidentally storing sensitive values.

- Detect obvious secrets in `put`, `mirror-file`, and `import-json`.
- Cover common patterns such as private key blocks, API/token-looking values, credentialed URLs, `password=`, `secret=`, and `connection string` credentials.
- Block by default with a clear validation error.
- Add an explicit override such as `--allow-sensitive` for rare intentional local-only cases.
- Document that detection is best-effort and not a substitute for review.
- Add service and CLI tests for blocked, allowed, and false-positive-sensitive cases.

### Phase 10: Doctor Command

Phase 10 status: complete. See `docs/DOCTOR.md`.

Add a diagnostic command for real-repo setup and ongoing maintenance.

- Add `agent-memory doctor --json`.
- Check database path resolution, database existence, schema version, WAL mode, FTS backend, writable/readable status, ignored live DB files, tracked snapshot presence, tracked Markdown export presence, and snapshot restore viability.
- Report warnings separately from failures.
- Keep human output concise and JSON output script-friendly.
- Add tests for healthy, missing database, missing snapshot, and stale export conditions.

### Phase 11: Complete Snapshot Coverage

Phase 11 status: complete. JSON snapshots now include semantic memories and mirrored file revisions.

Make tracked memory handoff complete enough for another computer to recreate useful project context.

- Include `mirrored_files` revisions in `export-json`.
- Restore mirrored file revisions in `import-json`.
- Keep existing keyed memory import idempotent.
- Make mirrored-file import idempotent by `project + path + content_sha256`.
- Update `docs/MEMORY_SYNC.md` with the expanded snapshot contract.
- Add restore tests that verify memories and mirrored file revisions.

### Phase 12: Backup and Restore Polish

Phase 12 status: complete. Export/import now supports dry-run validation, verified export restore, and unkeyed-memory warnings.

Make export/import safer to run before checkin and during onboarding.

- Add `import-json --dry-run`.
- Add snapshot validation that reports all detected problems before mutating the database.
- Add `export-json --verify` or an equivalent verification flow that imports into a temporary database and checks expected counts.
- Consider warning when unkeyed memories are present because repeated imports create new rows.
- Document the recommended pre-checkin command sequence.

### Phase 13: Agent Onboarding Instructions

Phase 13 status: complete. The CLI now prints agent-facing instructions and installs an idempotent managed section in agent instruction files.

Teach local agents how to use a global CLI without requiring each user to paste instructions every time.

- Add `agent-memory instructions` with concise Markdown output for agents.
- Add `agent-memory instructions --json` for scriptable discovery.
- Add an idempotent installer for an agent-memory section in `AGENTS.md` or a chosen output file.
- Explain the global CLI limitation: plain CLIs are not automatically discoverable by models, unlike MCP tools.
- Document the future MCP path where tools, resources, and prompts make the workflow discoverable through the client.
- Add tests for instruction output and idempotent section replacement.

### Phase 14: Production Usage Guide

Phase 14 status: complete. See `docs/PRODUCTION_USAGE.md`.

Document how to use the tool responsibly in real application repositories.

- Explain what to store and what not to store.
- Provide project bootstrap snippets for `AGENTS.md` and `CLAUDE.md`.
- Document memory as advisory context, never executable authority.
- Document local DB privacy, tracked exports, review expectations, and restore workflow.
- Include examples for production-safe command, decision, architecture, constraint, and workaround memories.
- Document which `.md` files are worth mirroring and that mirroring is explicit, not automatic.

### Phase 15: Cross-Project and Global Memory Sharing

Phase 15 status: complete. See `docs/CROSS_PROJECT_MEMORY.md`.

Support useful memory reuse without making global memory the default.

- Keep project-local databases as the recommended default for reproducible project context.
- Document global databases as an advanced personal mode with clear privacy and context-bleed tradeoffs.
- Define conventions for reusable memory projects such as `global`, `personal-patterns`, or `org-patterns`.
- Document search workflows that check both the current project and reusable memory contexts.
- Add `copy` for moving a selected memory from one project to another; defer filtered export/import until real usage shows it is needed.
- Keep any cross-project sharing explicit so unrelated projects do not silently inherit stale or unsafe context.

### Phase 16: Codex and Claude Skill Templates

Create reusable agent templates that teach agents to use the global CLI even when repository instructions are missing.

- Create a Codex skill template for `agent-memory` CLI usage.
- Create a Claude skill/template equivalent for the same workflow.
- Include install/discovery guidance, search-before-work workflow, memory write examples, `.md` mirroring, snapshot export, and restore commands.
- Include safety rules for secrets, advisory-only memory, and current user/repository instruction precedence.
- Include examples for personal installation and project bootstrap.
- Keep templates generic enough to copy into other projects or package later.

### Phase 17: Schema Migration Framework

Add migrations after the tool has been used long enough to know what should change.

- Keep this after the initial hardening work because the first real migration should be driven by actual usage.
- Implement an ordered migration framework before changing schema version `1`.
- Add backup-before-migrate behavior or a clear backup recommendation.
- Add tests for initializing a fresh schema and upgrading an older schema.
- Keep migrations simple and standard-library only unless a real need appears.

### Phase 18: CI and Release Validation

Add CI last because the project is not ready to be shared broadly yet and may not live on GitHub immediately.

- Add GitHub Actions or equivalent only when the repository is closer to being shared.
- Validate Windows, Linux, and macOS.
- Validate supported Python versions.
- Run pytest, build wheel/sdist, install the built artifact, and smoke-test the console script.
- Consider publishing/package checks after the sharing path is clearer.

## Deferred MCP Work

MCP remains future-state. It should stay optional and personal-development-oriented until the CLI is hardened. When revisited, the MCP adapter should call `MemoryService` directly and should not shell out to the CLI or duplicate SQL.
