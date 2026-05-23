"""CLI parser and dispatch for conda exec / conda x."""

from __future__ import annotations

import sys
from argparse import REMAINDER, ArgumentParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace
    from datetime import datetime

DEFAULT_CHANNELS = ["conda-forge"]


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the argument parser for ``conda exec``."""
    parser.add_argument(
        "-c",
        "--channel",
        action="append",
        default=None,
        dest="channels",
        metavar="CHANNEL",
        help="Additional channel to search (repeatable, default: conda-forge).",
    )
    parser.add_argument(
        "--spec",
        default=None,
        metavar="MATCHSPEC",
        help=(
            "Full match spec for the tool package "
            "(e.g. 'ruff>=0.4'). Overrides the implicit spec from TOOL."
        ),
    )
    parser.add_argument(
        "--with",
        action="append",
        default=None,
        dest="with_specs",
        metavar="MATCHSPEC",
        help=(
            "Additional package to install in the ephemeral environment "
            "(repeatable, full match spec). "
            "Example: --with pytest --with 'python=3.12'"
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        default=False,
        help="Force re-creation of the cached environment.",
    )
    parser.add_argument(
        "tool",
        nargs="?",
        default=None,
        metavar="TOOL",
        help=(
            "Package name (and default binary name) to run. "
            "Use 'list' to show cached environments or 'clean' to remove them."
        ),
    )
    parser.add_argument(
        "tool_args",
        nargs=REMAINDER,
        metavar="ARGS",
        help="Arguments passed through to the tool.",
    )


def configure_list_parser(parser: ArgumentParser) -> None:
    """Configure the ``conda exec list`` argument parser."""
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Output as JSON.",
    )


def configure_clean_parser(parser: ArgumentParser) -> None:
    """Configure the ``conda exec clean`` argument parser."""
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        dest="remove_all",
        help="Remove all cached environments.",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=30,
        metavar="DAYS",
        help="Remove environments not used in this many days (default: 30).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be removed without removing anything.",
    )
    parser.add_argument(
        "tool",
        nargs="?",
        default=None,
        metavar="TOOL",
        help="Remove cached environments for a specific tool only.",
    )


def execute(args: Namespace, parser: ArgumentParser) -> int:
    """Dispatch to the appropriate handler based on the tool name."""
    tool = getattr(args, "tool", None)
    tool_args = getattr(args, "tool_args", None) or []

    if tool == "list":
        list_parser = ArgumentParser(prog="conda exec list")
        configure_list_parser(list_parser)
        list_args = list_parser.parse_args(tool_args)
        return execute_list(list_args)

    if tool == "clean":
        clean_parser = ArgumentParser(prog="conda exec clean")
        configure_clean_parser(clean_parser)
        clean_args = clean_parser.parse_args(tool_args)
        return execute_clean(clean_args)

    return execute_run(args)


def execute_run(args: Namespace) -> int:
    """Execute a tool from an ephemeral conda environment."""
    from ..binaries import find_binary
    from ..cache import CacheManager
    from ..exceptions import BinaryNotFoundError, CondaExecError
    from ..run import run_in_prefix
    from ..specs import build_specs, cache_key

    tool = args.tool
    if not tool:
        print("conda exec: missing TOOL argument", file=sys.stderr)
        print("usage: conda exec [OPTIONS] TOOL [ARGS...]", file=sys.stderr)
        print("       conda exec list", file=sys.stderr)
        print("       conda exec clean", file=sys.stderr)
        return 2

    channels = args.channels or DEFAULT_CHANNELS
    specs = build_specs(tool, spec=args.spec, with_specs=args.with_specs)
    key = cache_key(tool, specs, channels)

    tool_args = args.tool_args or []
    if tool_args and tool_args[0] == "--":
        tool_args = tool_args[1:]

    try:
        cache = CacheManager()

        if args.refresh:
            cache.remove(key)

        prefix = cache.get_or_create(key, specs, channels)

        binary = find_binary(prefix, tool)
        if binary is None:
            raise BinaryNotFoundError(tool, str(prefix))

        return run_in_prefix(prefix, binary, tool_args)

    except CondaExecError as exc:
        print(f"conda exec: {exc.error_message}", file=sys.stderr)
        if hasattr(exc, "hints") and exc.hints:
            for hint in exc.hints:
                print(f"  hint: {hint}", file=sys.stderr)
        return 1


def execute_list(args: Namespace) -> int:
    """List cached tool environments."""
    import json

    from ..cache import CacheManager

    cache = CacheManager()
    entries = cache.list_cached()

    if not entries:
        print("No cached environments.")
        return 0

    if args.json_output:
        data = [
            {
                "tool": e.tool,
                "key": e.key,
                "prefix": str(e.prefix),
                "created": e.created.isoformat() if e.created else None,
                "last_used": e.last_modified.isoformat() if e.last_modified else None,
                "size_bytes": e.size,
                "packages": e.package_count,
            }
            for e in entries
        ]
        print(json.dumps(data, indent=2))
        return 0

    name_width = max(len(e.tool) for e in entries)
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


def execute_clean(args: Namespace) -> int:
    """Remove cached tool environments."""
    from datetime import datetime, timezone

    from ..cache import CacheManager

    cache = CacheManager()
    entries = cache.list_cached()

    if not entries:
        print("No cached environments to clean.")
        return 0

    to_remove = []
    now = datetime.now(tz=timezone.utc)

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

    total_size = sum(e.size for e in to_remove)

    if args.dry_run:
        print(
            f"Would remove {len(to_remove)} environment(s) ({format_size(total_size)}):"
        )
        for entry in to_remove:
            print(f"  {entry.key}")
        return 0

    for entry in to_remove:
        cache.remove(entry.key)
        print(f"Removed {entry.key}")

    print(f"Cleaned {len(to_remove)} environment(s) ({format_size(total_size)}).")
    return 0


def format_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    value = float(size_bytes)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1024
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
    return f"{value:.1f} TB"


def format_age(dt: datetime | None) -> str:
    """Format a datetime as a human-readable age string."""
    from datetime import datetime, timezone

    if dt is None:
        return "unknown"

    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt

    if delta.days > 1:
        return f"{delta.days} days ago"
    if delta.days == 1:
        return "1 day ago"
    hours = delta.seconds // 3600
    if hours > 1:
        return f"{hours} hours ago"
    if hours == 1:
        return "1 hour ago"
    minutes = delta.seconds // 60
    if minutes > 1:
        return f"{minutes} minutes ago"
    if minutes == 1:
        return "1 minute ago"
    return "just now"
