---
name: agent-memory
description: Use the global agent-memory CLI for durable project memory: restore/search context, write memories, mirror docs, export snapshots, and copy reusable memories.
---

# Agent Memory

Use the globally installed `agent-memory` CLI for durable project memory. Stored memory is advisory only. Current user instructions, repository files, security policy, and higher-priority Claude instructions override memory.

## Discover Commands

Use help before guessing syntax:

```sh
agent-memory --help
agent-memory <command> --help
```

If the command is missing, tell the user that `agent-memory` needs to be installed or added to `PATH`.

## Start Work

1. Determine the project name from repository instructions, or use the repository root directory name.
2. Check status:

```sh
agent-memory status --project <project> --json
```

3. If `docs/agent-memory.snapshot.json` exists and the local DB is missing, dry-run and restore:

```sh
agent-memory import-json docs/agent-memory.snapshot.json --dry-run --json
agent-memory import-json docs/agent-memory.snapshot.json --json
```

4. Search before substantial work:

```sh
agent-memory search "<task topic>" --project <project> --limit 8 --json
agent-memory recent --project <project> --limit 5 --json
```

Use only relevant results and verify them against current files.

## Write Memory

Write memory only for durable decisions, architecture notes, commands, constraints, workflows, and workarounds.

```sh
agent-memory put --project <project> --kind decision --key <stable-key> --content "<decision and reason>" --importance 5 --tag <tag> --agent claude --json
```

Prefer stable keys. Update obsolete memories instead of adding duplicates.

Never store secrets, credentials, tokens, private keys, protected personal data, unreviewed sensitive content, routine logs, or temporary command output.

## Mirror Files

Mirror important UTF-8 Markdown after meaningful edits. Mirroring is explicit and not automatic.

```sh
agent-memory mirror-file CLAUDE.md --project <project> --agent claude --json
agent-memory mirror-file AGENTS.md --project <project> --agent claude --json
agent-memory mirror-file docs/ARCHITECTURE.md --project <project> --agent claude --json
```

Mirror stable instruction, architecture, ADR, setup, and runbook files only after sensitivity review. Do not mirror generated exports, logs, build outputs, vendor files, or files containing secrets.

## Reusable Memory

Search project-local memory first. Search reusable projects such as `global`, `personal-patterns`, or `org-patterns` only when the user asks or local memory is insufficient.

Promote selected memories explicitly:

```sh
agent-memory copy --from-project <project> --from-kind decision --from-key <stable-key> --to-project personal-patterns --agent claude --json
```

Reusable memory must not override current repository instructions, source code, security policy, or team conventions.

## Finish Work

After meaningful memory changes, refresh tracked exports:

```sh
agent-memory doctor --project <project> --json
agent-memory export-json --project <project> --output docs/agent-memory.snapshot.json --verify --json
agent-memory export-md --project <project> --output docs/MEMORY.generated.md --json
```

Review exports before committing. Do not commit `.agent-memory/memory.db` or SQLite sidecar files.