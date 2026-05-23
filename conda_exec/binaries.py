"""Binary discovery in conda prefixes."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

from conda.common.path import BIN_DIRECTORY

if TYPE_CHECKING:
    from pathlib import Path


def find_binary(prefix: Path, name: str) -> Path | None:
    """Find a specific binary by name in a conda prefix.

    Checks the platform-correct bin directory (``bin/`` on Unix,
    ``Scripts/`` on Windows). On Windows, tries ``.exe``, ``.bat``,
    and ``.cmd`` extensions.
    """
    from conda.common.compat import on_win

    bin_dir = prefix / BIN_DIRECTORY
    if not bin_dir.is_dir():
        return None

    if on_win:
        for ext in (".exe", ".bat", ".cmd", ""):
            candidate = bin_dir / f"{name}{ext}"
            if candidate.is_file():
                if is_within_prefix(candidate, prefix):
                    return candidate
    else:
        candidate = bin_dir / name
        if candidate.is_file():
            if is_within_prefix(candidate, prefix):
                return candidate

    return None


def discover_binaries(prefix: Path) -> list[str]:
    """Return a list of executable binary names in a conda prefix.

    Looks in the platform-correct bin directory.
    """
    from conda.common.compat import on_win

    bin_dir = prefix / BIN_DIRECTORY
    if not bin_dir.is_dir():
        return []

    binaries = []
    for entry in sorted(bin_dir.iterdir()):
        if not entry.is_file():
            continue
        if on_win:
            if entry.suffix.lower() in (".exe", ".bat", ".cmd"):
                binaries.append(entry.stem)
        else:
            if is_executable(entry):
                binaries.append(entry.name)
    return binaries


def is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def is_within_prefix(path: Path, prefix: Path) -> bool:
    """Verify a binary resolves to a path within the prefix (symlink safety)."""
    try:
        return path.resolve().is_relative_to(prefix.resolve())
    except (OSError, ValueError):
        return False
