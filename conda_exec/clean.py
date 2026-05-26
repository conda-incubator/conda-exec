"""Clean cached tool environments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda import reporters
from conda.base.context import context
from conda.exceptions import CondaSystemExit

from .cache import CacheManager
from .format import format_size

if TYPE_CHECKING:
    from argparse import Namespace

    from .cache import CacheEntry


@dataclass(frozen=True)
class CleanResult:
    """Summary of removed cached environments."""

    removed_count: int
    total_size: int
    removed_keys: list[str]


def select_entries_for_cleaning(
    entries: list[CacheEntry],
    *,
    older_than: int,
    remove_all: bool = False,
    tool: str | None = None,
) -> list[CacheEntry]:
    """Select cached environments matching cleanup criteria."""
    to_remove = []
    now = datetime.now(tz=timezone.utc)

    for entry in entries:
        if tool and entry.tool != tool:
            continue
        if remove_all:
            to_remove.append(entry)
        elif entry.last_modified:
            age_days = (now - entry.last_modified).total_seconds() / 86400
            if age_days > older_than:
                to_remove.append(entry)

    return to_remove


def remove_cache_entries(cache: CacheManager, entries: list[CacheEntry]) -> CleanResult:
    """Remove cached environments and return a summary."""
    total_size = sum(entry.size for entry in entries)
    removed_keys = []

    for entry in entries:
        cache.remove(entry.key)
        removed_keys.append(entry.key)

    return CleanResult(
        removed_count=len(removed_keys),
        total_size=total_size,
        removed_keys=removed_keys,
    )


def execute_clean(args: Namespace) -> int:
    """Remove cached tool environments."""
    cache = CacheManager()
    entries = cache.list_cached()

    if not entries:
        print("No cached environments to clean.")
        return 0

    dry_run = args.dry_run or context.dry_run
    to_remove = select_entries_for_cleaning(
        entries,
        older_than=args.older_than,
        remove_all=args.remove_all,
        tool=args.tool,
    )

    if not to_remove:
        print("Nothing to clean.")
        return 0

    total_size = sum(entry.size for entry in to_remove)

    if dry_run:
        print(
            f"Would remove {len(to_remove)} environment(s) ({format_size(total_size)}):"
        )
        for entry in to_remove:
            print(f"  {entry.key}")
        return 0

    if not args.yes:
        print(
            f"Will remove {len(to_remove)} environment(s) ({format_size(total_size)}):"
        )
        for entry in to_remove:
            print(f"  {entry.key}")
        try:
            reporters.confirm_yn()
        except (CondaSystemExit, EOFError):
            print("Aborted.")
            return 1

    result = remove_cache_entries(cache, to_remove)
    for key in result.removed_keys:
        print(f"Removed {key}")

    print(f"Cleaned {result.removed_count} environment(s) ({format_size(total_size)}).")
    return 0
