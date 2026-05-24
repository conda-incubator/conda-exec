"""CLI parser and dispatch for conda exec / conda x."""

from __future__ import annotations

import sys
from argparse import REMAINDER, ArgumentParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

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


SUBCOMMANDS: dict[str, tuple[str, str, str]] = {
    "list": (".list", "configure_list_parser", "execute_list"),
    "clean": (".clean", "configure_clean_parser", "execute_clean"),
}


def execute(args: Namespace) -> int:
    """Dispatch to the appropriate handler based on the tool name."""
    from importlib import import_module

    tool = getattr(args, "tool", None)
    tool_args = getattr(args, "tool_args", None) or []

    if tool in SUBCOMMANDS:
        module_path, configure_name, execute_name = SUBCOMMANDS[tool]
        mod = import_module(module_path, package=__package__)
        sub_parser = ArgumentParser(prog=f"conda exec {tool}")
        getattr(mod, configure_name)(sub_parser)
        sub_args = sub_parser.parse_args(tool_args)
        return getattr(mod, execute_name)(sub_args)

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
