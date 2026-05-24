"""List cached tool environments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .format import format_age, format_size

if TYPE_CHECKING:
    from argparse import Namespace


def execute_list(args: Namespace) -> int:
    """List cached tool environments."""
    import json

    from .cache import CacheManager

    cache = CacheManager()
    entries = cache.list_cached()

    if not entries:
        print("No cached environments.")
        return 0

    if args.json_output:
        data = [
            {
                "tool": entry.tool,
                "key": entry.key,
                "prefix": str(entry.prefix),
                "created": entry.created.isoformat() if entry.created else None,
                "last_used": (
                    entry.last_modified.isoformat() if entry.last_modified else None
                ),
                "size_bytes": entry.size,
                "packages": entry.package_count,
            }
            for entry in entries
        ]
        print(json.dumps(data, indent=2))
        return 0

    name_width = max(len(entry.tool) for entry in entries)
    header_width = max(name_width, 4)
    print(f"{'Tool':<{header_width}}  {'Size':>8}  {'Last used':<16}  Packages")
    for entry in entries:
        size = format_size(entry.size)
        last_used = format_age(entry.last_modified)
        print(
            f"{entry.tool:<{header_width}}  {size:>8}  {last_used:<16}  "
            f"{entry.package_count}"
        )
    return 0
