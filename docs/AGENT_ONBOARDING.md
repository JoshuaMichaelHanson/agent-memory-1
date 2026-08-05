# Agent Onboarding Instructions

A globally installed `agent-memory` CLI is useful only after an agent knows it exists. Plain CLIs are not automatically discoverable by models, so Phase 13 adds commands that expose and install the bootstrap instructions directly from the CLI.

## Commands

Show Markdown instructions for the current project:

```powershell
agent-memory instructions --project agent-memory-1
```

Return the same guidance as JSON metadata:

```powershell
agent-memory instructions --project agent-memory-1 --json
```

Install or update a managed section in an agent instruction file:

```powershell
agent-memory install-instructions `
  --project agent-memory-1 `
  --output .\AGENTS.md `
  --json
```

The installer uses these markers:

```text
<!-- BEGIN agent-memory instructions -->
<!-- END agent-memory instructions -->
```

If both markers exist, only the managed section is replaced. If neither marker exists, the section is appended. If only one marker exists, the command fails so it does not corrupt hand-written instructions.

## Recommended Bootstrap

For a project using a global CLI and a project-local database:

1. Run `agent-memory install-instructions --project <project-name> --output AGENTS.md --json` once.
2. Review the inserted section before committing.
3. Ask agents to read `AGENTS.md` as normal.
4. After changing important Markdown instructions, run `agent-memory mirror-file AGENTS.md --project <project-name> --agent codex --json`.
5. Before checkin, run `export-json --verify` and `export-md`.

## Why This Exists

The default operating model is a global CLI install plus a project-local `.agent-memory/memory.db`. That keeps the executable easy to install while keeping memory state reproducible through tracked project exports.

The problem is discovery. If an agent starts in a repository with no local instructions, it may not know to run `agent-memory`. The `instructions` command gives users a single command to paste or install into local agent guidance. The generated section also tells agents to use `agent-memory --help` and `agent-memory <command> --help`, and to tell users those help commands exist instead of guessing syntax.

## MCP Future State

MCP can make this cleaner later because servers advertise capabilities through the client. A future MCP adapter can expose memory tools, resources, and prompt templates directly. Until then, `agent-memory instructions` and `install-instructions` are the simple CLI bridge.

## Safety

Stored memory is advisory context. Current user instructions and current repository files override stored memory. Do not store secrets, credentials, tokens, private keys, protected personal data, or unreviewed sensitive content.