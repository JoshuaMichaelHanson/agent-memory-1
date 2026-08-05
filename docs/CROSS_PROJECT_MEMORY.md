# Cross-Project and Global Memory

Phase 15 supports reusable memory without making global memory the default. The safe default remains one project-local database per repository, with explicit commands for checking or copying reusable context.

## Recommended Default

Use a project-local database for normal work:

```powershell
agent-memory status --project my-service --json
agent-memory search "retry policy" --project my-service --limit 8 --json
```

With the default path resolver, this database lives at:

```text
.agent-memory/memory.db
```

Keep that live database ignored by Git. Share reproducible context through reviewed exports:

```powershell
agent-memory export-json --project my-service --output .\docs\agent-memory.snapshot.json --verify --json
agent-memory export-md --project my-service --output .\docs\MEMORY.generated.md --json
```

## Reusable Memory Projects

When a memory is useful outside one repository, store it under an explicit reusable project name instead of letting every repository silently inherit it.

Suggested names:

- `global` for rare personal facts or preferences that apply almost everywhere.
- `personal-patterns` for reusable engineering preferences, debugging habits, and common command patterns.
- `org-patterns` for non-sensitive organization conventions that are approved to share with the selected developer group.
- `python-patterns`, `javascript-patterns`, or `java-patterns` for language-specific practices.
- `<domain>-patterns` for reusable domain rules that are not tied to one repository.

Keep reusable memories generic. If a decision depends on a specific repository, customer, incident, internal hostname, credential location, or private operational detail, leave it in the project-local context.

## Global Database Mode

A global database is an advanced personal mode. It can be useful for a developer's own patterns, but it increases privacy and context-bleed risk.

Windows example:

```powershell
agent-memory init --db "$env:USERPROFILE\.agent-memory\global-memory.db" --json
agent-memory put --db "$env:USERPROFILE\.agent-memory\global-memory.db" --project personal-patterns --kind workflow --key test-before-commit --content "Run the narrow test first, then the full suite before commit." --tag tests --json
```

macOS or Linux example:

```sh
agent-memory init --db "$HOME/.agent-memory/global-memory.db" --json
agent-memory put --db "$HOME/.agent-memory/global-memory.db" --project personal-patterns --kind workflow --key test-before-commit --content "Run the narrow test first, then the full suite before commit." --tag tests --json
```

Do not point `AGENT_MEMORY_DB` at a global database unless the user explicitly wants every repository in that shell session to use it. Prefer passing `--db` for global lookups so the active database is obvious in command history.

## Search Workflow

Search the current repository first:

```powershell
agent-memory search "database migration" --project my-service --limit 8 --json
```

If the local results are insufficient and the user has a reusable database, search reusable contexts explicitly:

```powershell
agent-memory search "database migration" --db "$env:USERPROFILE\.agent-memory\global-memory.db" --project personal-patterns --limit 5 --json
agent-memory search "database migration" --db "$env:USERPROFILE\.agent-memory\global-memory.db" --project org-patterns --limit 5 --json
```

On macOS or Linux:

```sh
agent-memory search "database migration" --db "$HOME/.agent-memory/global-memory.db" --project personal-patterns --limit 5 --json
agent-memory search "database migration" --db "$HOME/.agent-memory/global-memory.db" --project org-patterns --limit 5 --json
```

Only apply reusable memory after checking it against the current repository files and current user instructions.

## Copying Memory Between Projects

Use `copy` to promote one selected memory into another project inside the same database. The command is explicit so unrelated projects do not inherit context automatically.

Copy by keyed source lookup:

```powershell
agent-memory copy `
  --from-project my-service `
  --from-kind decision `
  --from-key idempotency-storage `
  --to-project personal-patterns `
  --agent codex `
  --json
```

Copy by source ID:

```powershell
agent-memory copy --id 42 --to-project global --agent codex --json
```

Override the target key when the reusable version should have a different name:

```powershell
agent-memory copy `
  --id 42 `
  --to-project personal-patterns `
  --to-key durable-idempotency-pattern `
  --agent codex `
  --json
```

`copy` defaults the target scope, kind, key, content, tags, source path, and importance from the source memory. The copied row is keyed by the target project, scope, kind, and key, so repeated copies update or report unchanged instead of creating duplicate rows.

Copying an unkeyed memory requires `--to-key` because repeated unkeyed imports and copies are not idempotent.

## Export and Import Sharing

For now, share reusable memory through normal project snapshots:

```powershell
agent-memory export-json --db "$env:USERPROFILE\.agent-memory\global-memory.db" --project personal-patterns --output .\personal-patterns.snapshot.json --verify --json
agent-memory import-json .\personal-patterns.snapshot.json --db "$env:USERPROFILE\.agent-memory\global-memory.db" --dry-run --json
agent-memory import-json .\personal-patterns.snapshot.json --db "$env:USERPROFILE\.agent-memory\global-memory.db" --json
```

This keeps sharing explicit. Filtered export/import may be added later if real usage shows that copying whole reusable projects is too broad.

## Privacy and Context-Bleed Risks

Global and reusable memory can accidentally carry assumptions into the wrong repository.

Review reusable memories for:

- Secrets, credentials, tokens, private keys, and protected personal data.
- Internal hostnames, account names, incident details, or customer-specific information.
- Repository-specific decisions that are not generally true.
- Stale conventions that changed in newer projects.
- Personal preferences that should not override team standards.

Current user instructions and current repository files always override reusable memory.
