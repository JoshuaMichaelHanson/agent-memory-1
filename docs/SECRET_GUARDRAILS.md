# Secret Guardrails

Phase 9 adds best-effort checks to reduce accidental storage of sensitive values.

## Commands Checked

The guardrail runs before database mutation for:

- `put`
- `mirror-file`
- `import-json`

The same checks live in the service layer, so future adapters such as MCP should get the default protection without duplicating CLI logic.

## Patterns Detected

The scanner blocks obvious examples of:

- private key blocks containing standard PEM private-key headers
- credentialed URLs containing both a username and password
- authorization bearer token headers
- secret-like assignments such as `password=...`, `token=...`, `api_key=...`, `client_secret=...`, or `connection_string=...`
- common token formats such as AWS access keys and GitHub tokens

Policy text that mentions passwords, API keys, or tokens without including values is allowed.

## Override

Use `--allow-sensitive` only when storage is intentional and local-only:

```powershell
python -m agent_memory put `
  --project demo `
  --content "<intentional local-only sensitive content>" `
  --allow-sensitive `
  --json
```

The override exists for edge cases. It does not make tracked exports safe to commit.

## Limitations

This is best-effort detection, not comprehensive secret scanning. It will miss some secrets and may block some false positives. Users and agents must still review memory content and tracked exports before committing.
