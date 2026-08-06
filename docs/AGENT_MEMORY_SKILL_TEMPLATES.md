# Agent Memory Skill Templates

Phase 16 provides copyable Codex and Claude templates that teach agents to use a globally installed `agent-memory` CLI even when a repository does not yet have local instructions.

## Templates

- Codex: `examples/codex-skill-template/agent-memory/SKILL.md`
- Codex UI metadata: `examples/codex-skill-template/agent-memory/agents/openai.yaml`
- Claude: `examples/claude-skill-template/agent-memory/SKILL.md`

The templates intentionally avoid scripts and extra references. The workflow is command-driven and should stay small enough for an agent to load directly.

## Codex Install

Copy the template into a personal Codex skills directory:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills\agent-memory" | Out-Null
Copy-Item .\examples\codex-skill-template\agent-memory\SKILL.md "$env:USERPROFILE\.codex\skills\agent-memory\SKILL.md"
Copy-Item -Recurse .\examples\codex-skill-template\agent-memory\agents "$env:USERPROFILE\.codex\skills\agent-memory\agents"
```

POSIX shell:

```sh
mkdir -p "$HOME/.codex/skills/agent-memory"
cp examples/codex-skill-template/agent-memory/SKILL.md "$HOME/.codex/skills/agent-memory/SKILL.md"
cp -R examples/codex-skill-template/agent-memory/agents "$HOME/.codex/skills/agent-memory/agents"
```

Use a project-local copy instead when a repository should carry the skill with it:

```text
.codex/skills/agent-memory/SKILL.md
```

## Claude Install

For Claude Code personal use, copy the template into the personal skills directory:

```sh
mkdir -p "$HOME/.claude/skills/agent-memory"
cp examples/claude-skill-template/agent-memory/SKILL.md "$HOME/.claude/skills/agent-memory/SKILL.md"
```

For a project-local Claude Code skill, copy it into:

```text
.claude/skills/agent-memory/SKILL.md
```

Claude.ai upload flows may require packaging the skill directory as a ZIP and may refer to the entry file as `skill.md`. Keep the template content the same and follow the current Claude upload UI requirements when packaging.

## Expected Agent Workflow

Both templates teach the same sequence:

1. Use `agent-memory --help` and `agent-memory <command> --help` for command discovery.
2. Run `agent-memory status --project <project> --json`.
3. Restore `docs/agent-memory.snapshot.json` when the local database is missing.
4. Search project memory before substantial work.
5. Write durable keyed memories with `put`.
6. Mirror important Markdown explicitly with `mirror-file`.
7. Search/copy reusable memory only when useful and explicit.
8. Run `doctor`, `export-json --verify`, and `export-md` before checkin.

## Safety Rules

The templates state that memory is advisory. Current user instructions, repository files, security policy, and higher-priority agent instructions override stored memory.

Agents must not store secrets, credentials, tokens, private keys, protected personal data, unreviewed sensitive content, routine logs, or temporary command output.

## Example Test Prompts

After installing the Codex template, start a fresh session in a repository and ask:

```text
Use agent-memory to check whether this project has durable memory, then search for testing workflow guidance.
```

After installing the Claude template, start Claude Code in a repository and ask:

```text
Use your agent-memory skill to restore/search project memory, then tell me the safest test command to run.
```

For either agent, verify that it checks `agent-memory --help` when uncertain, searches before acting, and does not treat memory as higher authority than repository files.