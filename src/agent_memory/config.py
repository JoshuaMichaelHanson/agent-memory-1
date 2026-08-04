from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MEMORY_DIR = ".agent-memory"
DEFAULT_DATABASE_NAME = "memory.db"
ENV_DATABASE_PATH = "AGENT_MEMORY_DB"


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    database_path: Path
    project_root: Path
    source: str


def detect_project_root(cwd: Path | None = None) -> Path:
    start = (cwd or Path.cwd()).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            text=True,
            capture_output=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return start

    if result.returncode != 0:
        return start

    root = result.stdout.strip()
    if not root:
        return start
    return Path(root).resolve()


def resolve_config(db_path: Path | str | None = None, cwd: Path | None = None) -> MemoryConfig:
    project_root = detect_project_root(cwd)

    if db_path is not None:
        raw_path = Path(db_path)
        source = "cli"
    else:
        env_path = os.environ.get(ENV_DATABASE_PATH)
        if env_path:
            raw_path = Path(env_path)
            source = "environment"
        else:
            raw_path = project_root / DEFAULT_MEMORY_DIR / DEFAULT_DATABASE_NAME
            source = "default"

    if raw_path.is_absolute():
        database_path = raw_path.resolve()
    else:
        database_path = (Path(cwd or Path.cwd()).resolve() / raw_path).resolve()

    return MemoryConfig(
        database_path=database_path,
        project_root=project_root,
        source=source,
    )
