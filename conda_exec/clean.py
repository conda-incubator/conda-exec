"""Clean cached tool environments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .format import format_size

if TYPE_CHECKING:
    from argparse import Namespace


def execute_clean(args: Namespace) -> int:
    """Remove cached tool environments."""
    from datetime import datetime, timezone

    from conda.base.context import context
    from conda.exceptions import CondaSystemExit
    from conda.reporters import confirm_yn

    from .cache import CacheManager

    cache = CacheManager()
    entries = cache.list_cached()

    if not entries:
        print("No cached environments to clean.")
        return 0

    to_remove = []
    now = datetime.now(tz=timezone.utc)
    dry_run = args.dry_run or context.dry_run

    for entry in entries:
        if args.tool and entry.tool != args.tool:
            continue
        if args.remove_all:
            to_remove.append(entry)
        elif entry.last_modified:
            age_days = (now - entry.last_modified).total_seconds() / 86400
            if age_days > args.older_than:
                to_remove.append(entry)

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
            confirm_yn()
        except (CondaSystemExit, EOFError):
            print("Aborted.")
            return 1

    for entry in to_remove:
        cache.remove(entry.key)
        print(f"Removed {entry.key}")

    print(f"Cleaned {len(to_remove)} environment(s) ({format_size(total_size)}).")
    return 0
