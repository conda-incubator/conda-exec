"""Execute a tool from an ephemeral conda environment."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from conda.core import prefix_data
from conda.exceptions import InvalidMatchSpec
from conda.models.match_spec import MatchSpec
from packaging.specifiers import InvalidSpecifier, SpecifierSet

from . import binaries, run, script
from .cache import CacheManager
from .exceptions import (
    BinaryNotFoundError,
    CondaExecError,
    InvalidToolMatchSpecError,
    PyPIDependencyError,
    PythonVersionError,
)

if TYPE_CHECKING:
    from argparse import Namespace

DEFAULT_CHANNELS = ["conda-forge"]

SCRIPT_EXTENSIONS = {".py", ".pyw"}


def is_script_path(tool: str) -> bool:
    """Check if the tool argument looks like a script path."""
    return (
        "/" in tool
        or "\\" in tool
        or any(tool.endswith(ext) for ext in SCRIPT_EXTENSIONS)
    )


def strip_tool_separator(args: Namespace) -> list[str]:
    """Extract tool args from parsed args, stripping a leading ``--``."""
    tool_args = args.tool_args or []
    if tool_args and tool_args[0] == "--":
        tool_args = tool_args[1:]
    return tool_args


def print_exec_error(exc: CondaExecError) -> None:
    """Print a CondaExecError with its hints to stderr."""
    print(f"conda exec: {exc.error_message}", file=sys.stderr)
    for hint in exc.hints:
        print(f"  hint: {hint}", file=sys.stderr)


def print_created_message(label: str, start_time: float) -> None:
    """Print a creation timing message to stderr."""
    elapsed = time.monotonic() - start_time
    print(
        f"Creating environment for {label}... done ({elapsed:.1f}s)",
        file=sys.stderr,
        flush=True,
    )


def execute_run(args: Namespace) -> int:
    """Execute a tool from an ephemeral conda environment."""
    tool = args.tool
    if not tool:
        print("conda exec: missing TOOL argument", file=sys.stderr)
        print("usage: conda exec [OPTIONS] TOOL [ARGS...]", file=sys.stderr)
        print("       conda exec --list", file=sys.stderr)
        print("       conda exec --clean", file=sys.stderr)
        return 2

    script_path = Path(tool)
    if is_script_path(tool) and script_path.is_file():
        return execute_script(args, script_path)

    try:
        try:
            name = MatchSpec(tool).name
        except InvalidMatchSpec as exc:
            raise InvalidToolMatchSpecError(tool, str(exc)) from exc

        channels = args.channels or DEFAULT_CHANNELS
        specs = [tool] + (args.with_specs or [])
        tool_args = strip_tool_separator(args)

        cache = CacheManager()
        key = cache.cache_key(name, specs, channels)

        if args.refresh:
            cache.remove(key)

        start_time = time.monotonic()
        prefix, created = cache.get_or_create(key, specs, channels)

        if created:
            print_created_message(name, start_time)

        binary = binaries.find_binary(prefix, name)
        if binary is None:
            raise BinaryNotFoundError(name)

        return run.run_in_prefix(prefix, binary, tool_args, activate=args.activate)

    except CondaExecError as exc:
        print_exec_error(exc)
        return 1


def check_requires_python(prefix: Path, requires_python: str) -> None:
    """Validate the resolved Python against requires-python (PEP 440)."""
    pd = prefix_data.PrefixData(prefix)
    python_rec = pd.get("python", None)
    if python_rec is None:
        return

    try:
        specifier = SpecifierSet(requires_python)
    except InvalidSpecifier:
        return

    if python_rec.version not in specifier:
        raise PythonVersionError(requires_python, python_rec.version)


def execute_script(args: Namespace, script_path: Path) -> int:
    """Execute a Python script with PEP 723 inline metadata."""
    tool_args = strip_tool_separator(args)

    metadata = script.parse_script_metadata(str(script_path))

    has_metadata = metadata is not None
    has_pypi_deps = bool(metadata and metadata.pypi_dependencies)
    has_cli_extras = args.with_specs or args.channels

    if not has_metadata and not has_cli_extras:
        return run_script_directly(script_path, tool_args)

    try:
        if has_pypi_deps:
            from .pypi import is_available

            if not is_available():
                raise PyPIDependencyError

        cache = CacheManager()

        channels = list(metadata.conda_channels) if metadata else []
        if args.channels:
            channels.extend(args.channels)
        if not channels:
            channels = list(DEFAULT_CHANNELS)

        if has_pypi_deps:
            from .pypi import PYPI_CHANNEL

            if PYPI_CHANNEL not in channels:
                channels.append(PYPI_CHANNEL)

        specs = list(metadata.conda_dependencies) if metadata else []
        if has_pypi_deps:
            specs.extend(metadata.pypi_dependencies)
        if args.with_specs:
            specs.extend(args.with_specs)

        if not any(spec.startswith("python") for spec in specs):
            python_spec = "python"
            if metadata and metadata.requires_python:
                python_spec = f"python {metadata.requires_python}"
            specs.append(python_spec)

        key = cache.cache_key("script", specs, channels)

        if args.refresh:
            cache.remove(key)

        start_time = time.monotonic()
        prefix, created = cache.get_or_create(key, specs, channels)

        if created:
            print_created_message("script", start_time)

        if metadata and metadata.requires_python:
            check_requires_python(prefix, metadata.requires_python)

        python = binaries.find_python(prefix)
        if python is None:
            print(
                "conda exec: python not found in script environment",
                file=sys.stderr,
            )
            return 1

        return run.run_in_prefix(
            prefix,
            python,
            [str(script_path.resolve()), *tool_args],
            activate=args.activate,
        )

    except CondaExecError as exc:
        print_exec_error(exc)
        return 1


def run_script_directly(script_path: Path, args: list[str]) -> int:
    """Run a script with the current Python when no deps are declared."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script_path.resolve()), *args],
    )
    return result.returncode
