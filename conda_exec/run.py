"""Subprocess execution for ephemeral tool invocations."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from conda.common.path import BIN_DIRECTORY

if TYPE_CHECKING:
    from pathlib import Path


def build_activated_env(prefix: Path) -> dict[str, str]:
    """Build a subprocess environment with conda activation applied."""
    from conda.activate import CmdExeActivator, PosixActivator
    from conda.common.compat import on_win

    activator_cls = CmdExeActivator if on_win else PosixActivator
    activator = activator_cls()
    activation = activator.build_activate(str(prefix))

    env = os.environ.copy()
    env.update(activation.get("export_vars", {}))
    for var in activation.get("unset_vars", []):
        env.pop(var, None)
    return env


def run_in_prefix(
    prefix: Path,
    binary: Path,
    args: list[str],
    *,
    activate: bool = False,
) -> int:
    """Execute a binary from a conda prefix.

    When activate is False (default), prepends the prefix's bin directory
    to PATH. When activate is True, applies full conda activation
    (CONDA_PREFIX, custom env vars, etc.).

    Returns the tool's exit code.
    """
    if activate:
        env = build_activated_env(prefix)
    else:
        bin_dir = str(prefix / BIN_DIRECTORY)
        env = os.environ.copy()
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    try:
        result = subprocess.run(
            [str(binary), *args],
            env=env,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    except FileNotFoundError:
        print(f"conda exec: {binary.name}: command not found", file=sys.stderr)
        return 127
    except PermissionError:
        print(f"conda exec: {binary.name}: permission denied", file=sys.stderr)
        return 126

    return result.returncode
