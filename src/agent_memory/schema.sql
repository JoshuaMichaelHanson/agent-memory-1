CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO schema_metadata(key, value)
VALUES ('schema_version', '2')
ON CONFLICT(key) DO NOTHING;

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'project',
    kind TEXT NOT NULL DEFAULT 'note',

    memory_key TEXT,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',

    source_agent TEXT NOT NULL DEFAULT 'unknown',
    source_path TEXT,

    importance INTEGER NOT NULL DEFAULT 3
        CHECK (importance BETWEEN 1 AND 5),

    content_sha256 TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    last_accessed_at TEXT,
    access_count INTEGER NOT NULL DEFAULT 0,

    UNIQUE(project, scope, kind, memory_key)
);

CREATE INDEX IF NOT EXISTS idx_memories_project
    ON memories(project);

CREATE INDEX IF NOT EXISTS idx_memories_project_kind
    ON memories(project, kind);

CREATE INDEX IF NOT EXISTS idx_memories_project_importance
    ON memories(project, importance DESC);

CREATE INDEX IF NOT EXISTS idx_memories_updated
    ON memories(project, updated_at DESC);

CREATE TABLE IF NOT EXISTS mirrored_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    project TEXT NOT NULL,
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,

    source_agent TEXT NOT NULL DEFAULT 'unknown',

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    UNIQUE(project, path)
);

CREATE INDEX IF NOT EXISTS idx_mirrored_files_project_path
    ON mirrored_files(project, path);
