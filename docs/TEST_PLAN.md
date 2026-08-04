# Test Plan

Tests should use temporary directories and temporary SQLite databases. They must not depend on the developer's home directory, global Git config, or a real project memory database.

## Smoke Tests

- `python -m agent_memory --help`
- `python -m agent_memory init --db <tmp>/memory.db --json`
- `python -m agent_memory status --db <tmp>/memory.db --json`

## Database Tests

- initialization is idempotent
- schema version exists
- WAL mode is enabled for file-backed databases
- busy timeout is configured
- foreign keys are enabled
- FTS5 availability is detected
- `LIKE` fallback can be forced or simulated

## Service Tests

- keyed insert
- keyed update
- keyed unchanged
- unkeyed inserts create separate rows
- tag normalization
- importance validation
- line-ending normalization for content hashes
- `created_at` survives updates
- `updated_at` changes on updates

## Retrieval Tests

- get by ID
- get by compound key
- missing record behavior
- default touch increments `access_count`
- `--no-touch` leaves metadata unchanged
- recent ordering is deterministic

## Search Tests

- content search
- tag search
- project isolation
- scope and kind filters
- minimum importance filter
- limit handling
- malformed FTS query handling
- Unicode storage and search

## CLI Tests

- human output
- JSON output
- exit codes
- stdin content
- mutually exclusive content source validation
- `--db` overrides `AGENT_MEMORY_DB`
- `AGENT_MEMORY_DB` overrides default path
- command works through `python -m agent_memory`

## Mirror and Export Tests

- first mirror inserts
- identical mirror is unchanged
- changed mirror creates a new revision
- missing file returns file operation error
- generated Markdown warning header is present
- export groups by kind
- export order is stable
- output directory is created
- atomic replacement does not leave stale partial output
