"""CLI parser and dispatch for conda exec / conda x."""

from __future__ import annotations

from argparse import REMAINDER, ArgumentParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

SUBCOMMANDS: dict[str, tuple[str, str, str]] = {
    "list": (".list", "configure_list_parser", "execute_list"),
    "clean": (".clean", "configure_clean_parser", "execute_clean"),
}


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
            "Activate the environment before running the tool "
            "(sets CONDA_PREFIX, etc.)."
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
            "Package to run, as a name or full matchspec "
            "(e.g. 'ruff' or 'ruff>=0.4'). "
            "Use 'list' to show cached environments or 'clean' to remove them."
        ),
    )
    parser.add_argument(
        "tool_args",
        nargs=REMAINDER,
        metavar="ARGS",
        help="Arguments passed through to the tool.",
    )


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

    from .run import execute_run

    return execute_run(args)
