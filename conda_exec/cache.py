"""Ephemeral environment cache management."""

from __future__ import annotations

import hashlib
import logging
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.core import prefix_data
from conda.core.envs_manager import unregister_env
from conda.exceptions import CondaError
from conda.gateways.disk.delete import rm_rf
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec

from .exceptions import SolveError, SolverNotAvailableError

if TYPE_CHECKING:
    from datetime import datetime

    from .script import ScriptMetadata

log = logging.getLogger(__name__)

MAX_ENV_NAME_LEN = 200

SAFE_TOOL_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.+-]*$")
SAFE_KEY_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.+-]*--[0-9a-f]+$")


@dataclass(frozen=True)
class CacheEntry:
    """Metadata for a cached tool environment."""

    key: str
    tool: str
    prefix: Path
    created: datetime | None
    last_modified: datetime | None
    size: int
    package_count: int


class CacheManager:
    """Manages cached conda environments for ephemeral tool execution."""

    def __init__(self, envs_dir: Path | None = None) -> None:
        if envs_dir is None:
            from .paths import envs_dir as _default_envs_dir

            envs_dir = _default_envs_dir()
        self.envs_dir = envs_dir

    def get_or_create(
        self,
        key: str,
        specs: list[str],
        channels: list[str],
    ) -> tuple[Path, bool]:
        """Return a cached prefix and whether it was newly created."""
        prefix = self.prefix_for(key)
        if prefix.is_dir() and (prefix / "conda-meta").is_dir():
            self.touch(prefix)
            return prefix, False
        return self.create(key, specs, channels), True

    def create(
        self,
        key: str,
        specs: list[str],
        channels: list[str],
    ) -> Path:
        """Create a new cached environment via conda's solver.

        Uses a temporary directory and atomic rename to prevent
        partial environments from being visible on crash.
        """
        solver_backend = context.plugin_manager.get_cached_solver_backend()
        if solver_backend is None:
            raise SolverNotAvailableError

        final_prefix = self.prefix_for(key)
        self.envs_dir.mkdir(parents=True, exist_ok=True)
        tmp_prefix = Path(tempfile.mkdtemp(dir=self.envs_dir, prefix=".tmp-"))

        tool = key.rsplit("--", 1)[0]

        try:
            channel_objs = [Channel(c) for c in channels]
            match_specs = [MatchSpec(s) for s in specs]

            solver = solver_backend(
                str(tmp_prefix),
                channel_objs,
                context.subdirs,
                specs_to_add=match_specs,
            )
            transaction = solver.solve_for_transaction()
        # SystemExit: some solver backends call sys.exit() on failure
        except (CondaError, SystemExit) as exc:
            rm_rf(tmp_prefix)
            raise SolveError(tool, str(exc)) from exc

        try:
            transaction.download_and_extract()
            transaction.execute()
            tmp_prefix.rename(final_prefix)
        except CondaError as exc:
            rm_rf(tmp_prefix)
            raise SolveError(tool, str(exc)) from exc
        except OSError:
            rm_rf(tmp_prefix)
            if final_prefix.is_dir() and (final_prefix / "conda-meta").is_dir():
                return final_prefix
            raise
        except BaseException:
            rm_rf(tmp_prefix)
            raise

        return final_prefix

    def exists(self, key: str) -> bool:
        """Check if a cached environment exists (fast stat-only check)."""
        prefix = self.prefix_for(key)
        return prefix.is_dir() and (prefix / "conda-meta").is_dir()

    def remove(self, key: str) -> None:
        """Remove a cached environment."""
        prefix = self.prefix_for(key)
        if prefix.exists():
            unregister_env(str(prefix))
            prefix_data.PrefixData._cache_.clear()
            rm_rf(prefix)

    def list_cached(self) -> list[CacheEntry]:
        """Enumerate all cached environments with metadata."""
        if not self.envs_dir.is_dir():
            return []

        entries = []
        for path in sorted(self.envs_dir.iterdir()):
            if not path.is_dir() or "--" not in path.name:
                continue
            if path.name.startswith(".tmp-"):
                continue
            pd = prefix_data.PrefixData(path)
            if not pd.is_environment():
                continue

            tool = path.name.rsplit("--", 1)[0]
            package_count = len(list(pd.iter_records()))

            entries.append(
                CacheEntry(
                    key=path.name,
                    tool=tool,
                    prefix=path,
                    created=pd.created,
                    last_modified=pd.last_modified,
                    size=pd.size(),
                    package_count=package_count,
                )
            )
        return entries

    def cache_key(self, tool: str, specs: list[str], channels: list[str]) -> str:
        """Compute a deterministic cache key for a set of specs and channels.

        Returns ``{tool}--{hash}`` where hash is the first 16 hex characters
        of the SHA-256 of the sorted, normalized spec list and channel list.
        """
        if not tool:
            raise ValueError("tool name cannot be empty")
        if len(tool) > 128:
            raise ValueError(f"tool name too long: {len(tool)} characters")
        if not SAFE_TOOL_RE.match(tool):
            raise ValueError(
                f"invalid tool name: {tool!r} "
                "(must contain only alphanumeric, dash, dot, plus, underscore)"
            )
        normalized = sorted(str(MatchSpec(spec)) for spec in specs)
        blob = "|".join(normalized) + "||" + "|".join(sorted(channels))
        key_hash = hashlib.sha256(blob.encode()).hexdigest()[:16]
        return f"{tool}--{key_hash}"

    def prefix_for(self, key: str) -> Path:
        if len(key) > MAX_ENV_NAME_LEN:
            raise ValueError(f"cache key too long: {len(key)} > {MAX_ENV_NAME_LEN}")
        if not SAFE_KEY_RE.match(key):
            raise ValueError(f"invalid cache key: {key!r}")
        prefix = self.envs_dir / key
        resolved = prefix.resolve()
        if not resolved.is_relative_to(self.envs_dir.resolve()):
            raise ValueError(f"cache key escapes envs directory: {key!r}")
        return prefix

    def script_cache_key(self, metadata: ScriptMetadata) -> str:
        """Compute a deterministic cache key for script metadata.

        Returns ``script--{hash}`` where hash is the first 16 hex
        characters of the SHA-256 of all dependency information.
        """
        parts = [
            "|".join(sorted(metadata.conda_dependencies)),
            "|".join(sorted(metadata.pypi_dependencies)),
            "|".join(sorted(metadata.conda_channels)),
            metadata.requires_python or "",
        ]
        blob = "||".join(parts)
        key_hash = hashlib.sha256(blob.encode()).hexdigest()[:16]
        return f"script--{key_hash}"

    def touch(self, prefix: Path) -> None:
        """Update the history file mtime for staleness tracking.

        Skips the update if the file was touched within the last hour.
        """
        try:
            history = prefix / "conda-meta" / "history"
            if time.time() - history.stat().st_mtime < 3600:
                return
            history.touch()
        except FileNotFoundError:
            pass
