"""Conda plugin registration for conda-exec.

This module is imported on every conda invocation via the entry point
system. Only ``hookimpl`` and type imports are used at module level;
everything else is lazily imported inside the hooks to keep the
overhead under 1 ms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins import hookimpl

if TYPE_CHECKING:
    from collections.abc import Iterable

    from conda.plugins.types import CondaSubcommand


@hookimpl
def conda_subcommands() -> Iterable[CondaSubcommand]:
    from conda.plugins.types import CondaSubcommand

    from .cli import configure_parser, execute

    yield CondaSubcommand(
        name="exec",
        summary="Run a command from a conda package without installing it.",
        action=execute,
        configure_parser=configure_parser,
    )
