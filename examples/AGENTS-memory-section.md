## Persistent project memory

Durable project memory is stored in `.agent-memory/memory.db`.

Before beginning substantial work:

1. Search memory for the current task, relevant subsystem, known problems, and prior decisions.
2. Load only the most relevant results.
3. Treat current repository files and explicit user instructions as higher priority than stored memory.

Useful commands:

```text
agent-memory status --json
agent-memory search "<task topic>" --project "<project>" --limit 8 --json
agent-memory recent --project "<project>" --limit 5 --json
```

Before finishing substantial work:

1. Store only durable information that will help a future session.
2. Prefer a stable key so an existing memory is updated.
3. Do not store routine logs, temporary test output, guesses, secrets, credentials, tokens, or personal data.
4. Remove or update obsolete memories when a decision changes.

Example:

```text
agent-memory put \
  --project "<project>" \
  --kind decision \
  --key "<stable-key>" \
  --content "<durable fact or decision>" \
  --importance 4 \
  --agent codex \
  --json
```
