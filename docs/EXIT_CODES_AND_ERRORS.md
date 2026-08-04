# Exit Codes and Errors Plan

The CLI should expose stable, script-friendly exit codes and JSON error objects.

## Exit Codes

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 1 | General error |
| 2 | Invalid command-line usage |
| 3 | Database or schema error |
| 4 | Memory not found |
| 5 | Invalid content or validation error |
| 6 | File read or write error |

## Exception Mapping

| Exception | JSON code | Exit code |
| --- | --- | ---: |
| `AgentMemoryError` | `AGENT_MEMORY_ERROR` | 1 |
| `UsageError` | `USAGE_ERROR` | 2 |
| `DatabaseError` | `DATABASE_ERROR` | 3 |
| `MemoryNotFoundError` | `MEMORY_NOT_FOUND` | 4 |
| `ValidationError` | `VALIDATION_ERROR` | 5 |
| `FileOperationError` | `FILE_OPERATION_ERROR` | 6 |

## JSON Error Shape

When `--json` is active, stdout must contain exactly one JSON object:

```json
{
  "ok": false,
  "error": {
    "code": "MEMORY_NOT_FOUND",
    "message": "No memory matched the supplied key."
  }
}
```

Diagnostics and debug tracebacks belong on stderr. Tracebacks should require an explicit `--debug` option.
