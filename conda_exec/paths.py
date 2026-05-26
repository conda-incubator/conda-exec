"""Filesystem layout for conda-exec cached environments."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def data_dir() -> Path:
    """Return the base data directory for conda-exec.

    Resolution order:
    1. ``CONDA_EXEC_HOME`` environment variable (explicit override)
    2. ``~/.conda/exec/`` (primary, all platforms)
    3. On Windows only: ``platformdirs.user_data_dir("conda", "conda") / "exec"``
       as a fallback, matching conda's own behavior.
    """
    env = os.environ.get("CONDA_EXEC_HOME")
    if env:
        return Path(env).expanduser().resolve()

    primary = Path.home() / ".conda" / "exec"

    from conda.common.compat import on_win

    if on_win and not primary.exists():
        from platformdirs import user_data_dir

        return Path(user_data_dir("conda", "conda")) / "exec"

    return primary


def envs_dir() -> Path:
    """Return the directory for cached tool environments."""
    return data_dir() / "envs"


def run_count_file() -> Path:
    """Return the file used for the automatic cleanup invocation counter."""
    return data_dir() / "run-count"
