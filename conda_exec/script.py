"""PEP 723 inline script metadata parser."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .exceptions import ScriptMetadataError

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


@dataclass(frozen=True)
class ScriptBlocks:
    """Extracted script-adjacent metadata blocks."""

    script: str | None = None
    lock: str | None = None


def parse_script_metadata(path_or_text: str) -> ScriptMetadata | None:
    """Extract PEP 723 inline metadata from a Python script.

    Accepts either a file path or the script text directly. Returns
    None if no ``# /// script`` block is found.
    """
    from pathlib import Path

    script_path = Path(path_or_text)
    if script_path.is_file():
        if script_path.stat().st_size > MAX_SCRIPT_SIZE:
            return None
        with script_path.open(encoding="utf-8") as source_file:
            toml_str = extract_script_block(
                source_file,
                block_type="script",
                strict=True,
            )
    else:
        toml_str = extract_script_block(path_or_text, block_type="script", strict=True)

    if toml_str is None:
        return None

    return parse_script_metadata_block(toml_str)


def parse_script_metadata_block(toml_str: str) -> ScriptMetadata:
    """Parse PEP 723 TOML metadata content into structured metadata."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    try:
        data = tomllib.loads(toml_str)
    except Exception as exc:
        raise ScriptMetadataError(f"failed to parse TOML: {exc}") from exc

    requires_python = data.get("requires-python")
    pypi_deps = data.get("dependencies", [])

    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        raise ScriptMetadataError("'tool' must be a table")

    tool_conda = tool.get("conda", {})
    if not isinstance(tool_conda, dict):
        raise ScriptMetadataError("'tool.conda' must be a table")

    conda_deps = tool_conda.get("dependencies", [])
    conda_channels = tool_conda.get("channels", [])

    if requires_python is not None and not isinstance(requires_python, str):
        raise ScriptMetadataError("'requires-python' must be a string")
    if not isinstance(pypi_deps, list) or not all(
        isinstance(dep, str) for dep in pypi_deps
    ):
        raise ScriptMetadataError("'dependencies' must be a list of strings")
    if not isinstance(conda_deps, list) or not all(
        isinstance(dep, str) for dep in conda_deps
    ):
        raise ScriptMetadataError("'tool.conda.dependencies' must be a list of strings")
    if not isinstance(conda_channels, list) or not all(
        isinstance(channel, str) for channel in conda_channels
    ):
        raise ScriptMetadataError("'tool.conda.channels' must be a list of strings")

    return ScriptMetadata(
        requires_python=requires_python,
        pypi_dependencies=tuple(pypi_deps),
        conda_dependencies=tuple(conda_deps),
        conda_channels=tuple(conda_channels),
    )


def read_script_blocks(path: str, *, lock_block_type: str) -> ScriptBlocks:
    """Read script metadata and lock blocks from a script file in one pass."""
    from pathlib import Path

    script_path = Path(path)
    if script_path.stat().st_size > MAX_SCRIPT_SIZE:
        return ScriptBlocks()

    with script_path.open(encoding="utf-8") as source_file:
        blocks = extract_script_blocks(
            source_file,
            block_types=("script", lock_block_type),
            strict_block_types=("script",),
        )

    return ScriptBlocks(
        script=blocks.get("script"),
        lock=blocks.get(lock_block_type),
    )


def extract_script_block(
    source: str | Iterable[str],
    *,
    block_type: str = "script",
    strict: bool = False,
) -> str | None:
    """Extract the TOML content from a ``# /// script`` block.

    Follows PEP 723: scans for ``# /// script``, collects lines
    until ``# ///``, strips the ``# `` prefix from each line.
    Returns the raw TOML string or None if no block is found.

    Accepts a string (split on newlines) or any iterable of lines
    (e.g. an open file object) so large files can be read lazily.
    """
    blocks = extract_script_blocks(
        source,
        block_types=(block_type,),
        strict_block_types=(block_type,) if strict else (),
    )
    return blocks.get(block_type)


def extract_script_blocks(
    source: str | Iterable[str],
    *,
    block_types: Iterable[str],
    strict_block_types: Iterable[str] = (),
) -> dict[str, str]:
    """Extract one or more ``# ///`` metadata block types from source."""
    if isinstance(source, str):
        lines: Iterable[str] = source.splitlines()
    else:
        lines = (line.rstrip("\r\n") for line in source)

    wanted = set(block_types)
    strict = set(strict_block_types)
    results: dict[str, str] = {}

    collecting = False
    current_type: str | None = None
    current_invalid = False
    toml_lines: list[str] = []

    for line in lines:
        if not collecting:
            match = SCRIPT_MARKER_RE.match(line)
            if match and match.group("type") in wanted:
                collecting = True
                current_type = match.group("type")
                current_invalid = False
                toml_lines = []
            continue

        if SCRIPT_END_RE.match(line):
            if current_type is not None and not current_invalid:
                results.setdefault(current_type, "\n".join(toml_lines))
            collecting = False
            current_type = None
            current_invalid = False
            toml_lines = []
            continue

        if line.startswith("# "):
            toml_lines.append(line[2:])
        elif line == "#":
            toml_lines.append("")
        else:
            if current_type in strict:
                raise ScriptMetadataError(
                    "metadata block lines must start with '# ' or be '#'"
                )
            current_invalid = True

    if collecting:
        current_label = current_type or "unknown"
        if current_type in strict:
            raise ScriptMetadataError(f"unclosed '# /// {current_label}' block")
        print(
            f"conda exec: warning: unclosed '# /// {current_label}' block",
            file=sys.stderr,
        )

    return results
