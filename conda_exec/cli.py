"""CLI parser and dispatch for conda exec."""

from __future__ import annotations

from argparse import REMAINDER, Action
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Sequence

SCRIPT_EXTENSIONS = {".py", ".pyw"}


def tool_looks_like_script(tool: str) -> bool:
    """Return whether a tool argument uses script-path syntax."""
    return (
        "/" in tool
        or "\\" in tool
        or any(tool.endswith(ext) for ext in SCRIPT_EXTENSIONS)
    )


class ToolAction(Action):
    """Validate positional TOOL constraints that depend on earlier flags."""

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[object] | None,
        option_string: str | None = None,
    ) -> None:
        if values is not None and not isinstance(values, str):
            parser.error("TOOL must be a single argument")

        if values is not None and namespace.embed and not namespace.lock:
            parser.error("--embed requires --lock")
        if values is not None and namespace.lock:
            if not tool_looks_like_script(values) or not Path(values).is_file():
                parser.error("--lock is only supported for existing script files")
        setattr(namespace, self.dest, values)


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the argument parser for ``conda exec``."""
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--list",
        action="store_true",
        default=False,
        dest="list_mode",
        help="List cached environments.",
    )
    mode.add_argument(
        "--clean",
        action="store_true",
        default=False,
        dest="clean_mode",
        help="Remove cached environments.",
    )

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
        "--activate",
        action="store_true",
        default=False,
        help=(
            "Apply conda activation environment variables before running the tool "
            "(does not run activate.d shell scripts)."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        default=False,
        help="Force re-creation of the cached environment.",
    )
    parser.add_argument(
        "--lock",
        action="store_true",
        default=False,
        help="Write or use lock data for a script environment.",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        default=False,
        help=(
            "Embed generated lock data in the script instead of writing a "
            "sidecar lockfile."
        ),
    )
    parser.add_argument(
        "--ignore-lock",
        action="store_true",
        default=False,
        help="Ignore discovered script lock data and solve from script metadata.",
    )
    parser.add_argument(
        "--platform",
        action="append",
        default=None,
        dest="lock_platforms",
        metavar="SUBDIR",
        help="Platform/subdir to include when writing lock data (repeatable).",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Output as JSON (only with --list).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        dest="remove_all",
        help="Remove all cached environments (only with --clean).",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=30,
        metavar="DAYS",
        help=(
            "Remove environments not used in this many days "
            "(default: 30, only with --clean)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be removed without removing anything (--clean).",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Skip confirmation prompt (only with --clean).",
    )

    parser.add_argument(
        "tool",
        action=ToolAction,
        nargs="?",
        default=None,
        metavar="TOOL",
        help=(
            "Package to run, as a name or full matchspec (e.g. 'ruff' or 'ruff>=0.4')."
        ),
    )
    parser.add_argument(
        "tool_args",
        nargs=REMAINDER,
        metavar="ARGS",
        help="Arguments passed through to the tool.",
    )


def execute(args: Namespace) -> int:
    """Dispatch to the appropriate handler based on mode flags."""
    import sys

    if args.list_mode:
        from .list import execute_list

        return execute_list(args)

    if args.clean_mode:
        from .clean import execute_clean

        return execute_clean(args)

    if args.json_output:
        print(
            "conda exec: warning: --json is only used with --list",
            file=sys.stderr,
        )
    if args.dry_run:
        print(
            "conda exec: warning: --dry-run is only used with --clean",
            file=sys.stderr,
        )

    from .execute import execute_run

    rc = execute_run(args)
    if rc == 0:
        from .auto_clean import auto_clean_after_success

        auto_clean_after_success()
    return rc
