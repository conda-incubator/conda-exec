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

    from conda.plugins.types import CondaSetting, CondaSubcommand


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


@hookimpl
def conda_settings() -> Iterable[CondaSetting]:
    from conda.common.configuration import PrimitiveParameter
    from conda.plugins.types import CondaSetting

    from .config import (
        DEFAULT_AUTO_CLEAN,
        DEFAULT_CLEAN_AGE,
        DEFAULT_CLEAN_INTERVAL,
        validate_non_negative_int,
        validate_positive_int,
    )

    yield CondaSetting(
        name="conda_exec_auto_clean",
        description="Automatically prune stale conda-exec cached environments.",
        parameter=PrimitiveParameter(DEFAULT_AUTO_CLEAN, element_type=bool),
    )
    yield CondaSetting(
        name="conda_exec_clean_interval",
        description="Successful conda-exec runs between automatic cleanup checks.",
        parameter=PrimitiveParameter(
            DEFAULT_CLEAN_INTERVAL,
            element_type=int,
            validation=validate_positive_int,
        ),
    )
    yield CondaSetting(
        name="conda_exec_clean_age",
        description=(
            "Days since last use before automatic cleanup removes an environment."
        ),
        parameter=PrimitiveParameter(
            DEFAULT_CLEAN_AGE,
            element_type=int,
            validation=validate_non_negative_int,
        ),
    )
