"""PEP 723 inline script metadata parser."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

MAX_SCRIPT_SIZE = 10 * 1024 * 1024

SCRIPT_MARKER_RE = re.compile(r"^# /// (?P<type>[a-zA-Z0-9-]+)\s*$")
SCRIPT_END_RE = re.compile(r"^# ///$")


@dataclass(frozen=True)
class ScriptMetadata:
    """Parsed inline metadata from a Python script."""

    requires_python: str | None = None
    pypi_dependencies: tuple[str, ...] = ()
    conda_dependencies: tuple[str, ...] = ()
    conda_channels: tuple[str, ...] = ()


def parse_script_metadata(path_or_text: str) -> ScriptMetadata | None:
    """Extract PEP 723 inline metadata from a Python script.

    Accepts either a file path or the script text directly. Returns
    None if no ``# /// script`` block is found or if parsing fails.
    """
    from pathlib import Path

    script_path = Path(path_or_text)
    if script_path.is_file():
        if script_path.stat().st_size > MAX_SCRIPT_SIZE:
            return None
        with script_path.open(encoding="utf-8") as source_file:
            toml_str = extract_script_block(source_file)
    else:
        toml_str = extract_script_block(path_or_text)

    if toml_str is None:
        return None

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

    try:
        data = tomllib.loads(toml_str)
    except Exception as exc:
        print(
            f"conda exec: failed to parse inline metadata: {exc}",
            file=sys.stderr,
        )
        return None

    requires_python = data.get("requires-python")
    pypi_deps = data.get("dependencies", [])

    tool_conda = data.get("tool", {}).get("conda", {})
    conda_deps = tool_conda.get("dependencies", [])
    conda_channels = tool_conda.get("channels", [])

    return ScriptMetadata(
        requires_python=requires_python,
        pypi_dependencies=tuple(pypi_deps),
        conda_dependencies=tuple(conda_deps),
        conda_channels=tuple(conda_channels),
    )


def extract_script_block(source: str | Iterable[str]) -> str | None:
    """Extract the TOML content from a ``# /// script`` block.

    Follows PEP 723: scans for ``# /// script``, collects lines
    until ``# ///``, strips the ``# `` prefix from each line.
    Returns the raw TOML string or None if no block is found.

    Accepts a string (split on newlines) or any iterable of lines
    (e.g. an open file object) so large files can be read lazily.
    """
    if isinstance(source, str):
        lines: Iterable[str] = source.splitlines()
    else:
        lines = (line.rstrip("\r\n") for line in source)

    collecting = False
    toml_lines: list[str] = []

    for line in lines:
        if not collecting:
            match = SCRIPT_MARKER_RE.match(line)
            if match and match.group("type") == "script":
                collecting = True
            continue

        if SCRIPT_END_RE.match(line):
            return "\n".join(toml_lines)

        if line.startswith("# "):
            toml_lines.append(line[2:])
        elif line == "#":
            toml_lines.append("")
        else:
            return None

    if collecting:
        print(
            "conda exec: warning: unclosed '# /// script' block",
            file=sys.stderr,
        )
        return None

    return None
