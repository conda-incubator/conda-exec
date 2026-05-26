"""Clean cached tool environments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda import reporters
from conda.base.context import context
from conda.exceptions import CondaSystemExit

from .cache import CacheManager
from .format import format_size

if TYPE_CHECKING:
    from argparse import Namespace


def execute_clean(args: Namespace) -> int:
    """Remove cached tool environments."""
    cache = CacheManager()
    entries = cache.list_cached()

    if not entries:
        print("No cached environments to clean.")
        return 0

    dry_run = args.dry_run or context.dry_run
    to_remove = cache.cleanup_candidates(
        entries,
        older_than_days=args.older_than,
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

    result = cache.remove_entries(to_remove)
    for key in result.removed_keys:
        print(f"Removed {key}")

    print(f"Cleaned {result.removed_count} environment(s) ({format_size(total_size)}).")
    return 0
