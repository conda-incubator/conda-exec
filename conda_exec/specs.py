"""Spec normalization and cache key hashing."""

from __future__ import annotations

import hashlib
import re

SAFE_TOOL_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.+-]*$")


def validate_tool_name(tool: str) -> None:
    """Validate that a tool name is safe for use in filesystem paths."""
    if not tool:
        raise ValueError("tool name cannot be empty")
    if len(tool) > 128:
        raise ValueError(f"tool name too long: {len(tool)} characters")
    if not SAFE_TOOL_RE.match(tool):
        raise ValueError(
            f"invalid tool name: {tool!r} "
            "(must contain only alphanumeric, dash, dot, plus, underscore)"
        )


def cache_key(tool: str, specs: list[str], channels: list[str]) -> str:
    """Compute a deterministic cache key for a set of specs and channels.

    Returns ``{tool}--{hash}`` where hash is the first 16 hex characters
    of the SHA-256 of the sorted, normalized spec list and channel list.
    """
    from conda.models.match_spec import MatchSpec

    validate_tool_name(tool)
    normalized = sorted(str(MatchSpec(s)) for s in specs)
    blob = "|".join(normalized) + "||" + "|".join(sorted(channels))
    h = hashlib.sha256(blob.encode()).hexdigest()[:16]
    return f"{tool}--{h}"


def build_specs(
    tool: str,
    *,
    spec: str | None = None,
    with_specs: list[str] | None = None,
) -> list[str]:
    """Build the full list of specs from CLI arguments.

    The tool name is used as the base spec unless ``--spec`` overrides it.
    ``--with`` specs are appended.
    """
    base = spec if spec else tool
    result = [base]
    if with_specs:
        result.extend(with_specs)
    return result
