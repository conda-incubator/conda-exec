"""Automatic cache cleanup after successful tool execution."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

from .cache import CacheManager
from .config import get_auto_clean_config
from .format import format_size
from .paths import run_count_file

log = logging.getLogger(__name__)


def read_run_count(path: Path) -> int:
    """Read the best-effort invocation counter."""
    try:
        value = int(path.read_text().strip())
    except (FileNotFoundError, OSError, ValueError):
        return 0
    return max(value, 0)


def write_run_count(path: Path, count: int) -> None:
    """Write the invocation counter using tempfile and atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(f"{count}\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def increment_run_count(path: Path) -> int:
    """Increment the invocation counter and return the new value."""
    count = read_run_count(path) + 1
    write_run_count(path, count)
    return count


def auto_clean_after_success() -> None:
    """Run automatic cleanup when the configured invocation interval is reached."""
    try:
        config = get_auto_clean_config()
        if not config.enabled:
            return

        count_file = run_count_file()
        count = increment_run_count(count_file)
        if count < config.interval:
            return

        cache = CacheManager()
        entries = cache.cleanup_candidates(
            cache.list_cached(),
            older_than_days=config.age_days,
        )
        result = cache.remove_entries(entries)
        write_run_count(count_file, 0)

        if result.removed_count:
            print(
                "conda exec: "
                f"cleaned {result.removed_count} unused environment(s) "
                f"({format_size(result.total_size)} freed)",
                file=sys.stderr,
            )
    except Exception as exc:  # pragma: no cover - defensive best-effort cleanup
        log.debug("automatic cache cleanup skipped: %s", exc, exc_info=True)
