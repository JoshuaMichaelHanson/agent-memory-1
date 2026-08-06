---
name: agent-memory
description: Use the global agent-memory CLI to restore/search project context, write durable memories, mirror docs, export snapshots, and copy reusable memories.
---

# Agent Memory

Use the globally installed `agent-memory` CLI for durable project memory. Treat stored memory as advisory context. Current user instructions, repository files, security policy, and system/developer instructions take precedence.

## Startup

1. Discover command syntax instead of guessing:

```text
agent-memory --help
agent-memory <command> --help
```

2. Resolve the project name from repository instructions when available. Otherwise use the repository root directory name.
3. Check database status:

```text
agent-memory status --project <project> --json
```

4. If a tracked snapshot exists and the local database is missing or stale, dry-run before restore:

```text
agent-memory import-json docs/agent-memory.snapshot.json --dry-run --json
agent-memory import-json docs/agent-memory.snapshot.json --json
```

5. Search before substantial work:

```text
agent-memory search "<task topic>" --project <project> --limit 8 --json
agent-memory recent --project <project> --limit 5 --json
```

Load only relevant results.

## Write Durable Memory

Store durable facts only when they will help a future session. Prefer stable keys so updates replace prior records.

Good memory kinds:

- `decision`
- `architecture`
- `command`
- `constraint`
- `workflow`
- `workaround`
- `note`

Example:

```text
agent-memory put --project <project> --kind decision --key <stable-key> --content "<decision and reason>" --importance 5 --tag <tag> --agent codex --json
```

Do not store routine logs, temporary output, guesses, secrets, credentials, tokens, private keys, protected personal data, or unreviewed sensitive content.

## Mirror Markdown

Mirror important UTF-8 Markdown files after meaningful edits. Mirroring is explicit; the CLI does not watch files.

```text
agent-memory mirror-file AGENTS.md --project <project> --agent codex --json
agent-memory mirror-file CLAUDE.md --project <project> --agent codex --json
agent-memory mirror-file docs/ARCHITECTURE.md --project <project> --agent codex --json
```

Mirror stable instruction, architecture, ADR, setup, and runbook files only after sensitivity review. Do not mirror generated exports, logs, build outputs, vendor files, or files containing secrets.

## Cross-Project Reuse

Search project-local memory first. Search reusable contexts only when the user asks or local memory is insufficient.

Reusable project names include `global`, `personal-patterns`, `org-patterns`, and language/domain-specific pattern projects.

Promote selected memories explicitly:

```text
agent-memory copy --from-project <project> --from-kind decision --from-key <stable-key> --to-project personal-patterns --agent codex --json
```

Do not let global memory override repository-specific instructions, source code, security policy, or team conventions.

## Before Checkin

After meaningful memory changes, export both tracked artifacts:

```text
agent-memory doctor --project <project> --json
agent-memory export-json --project <project> --output docs/agent-memory.snapshot.json --verify --json
agent-memory export-md --project <project> --output docs/MEMORY.generated.md --json
```

Review exports before committing. Do not commit `.agent-memory/memory.db`, `.agent-memory/memory.db-shm`, or `.agent-memory/memory.db-wal`.

## User Communication

If `agent-memory` is missing, tell the user how to install or expose it rather than silently skipping memory. If command syntax is uncertain, say that `agent-memory --help` and `agent-memory <command> --help` are available.