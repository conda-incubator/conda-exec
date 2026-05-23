"""Ephemeral environment cache management."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .exceptions import SolveError, SolverNotAvailableError

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

log = logging.getLogger(__name__)

MAX_ENV_NAME_LEN = 200

_SAFE_KEY_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.+-]*--[0-9a-f]+$")


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
    ) -> Path:
        """Return a cached prefix, creating it if it does not exist."""
        prefix = self._prefix_for(key)
        if prefix.is_dir() and (prefix / "conda-meta").is_dir():
            self._touch(prefix)
            return prefix
        return self.create(key, specs, channels)

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
        from conda.base.context import context
        from conda.exceptions import UnsatisfiableError
        from conda.gateways.disk.delete import rm_rf
        from conda.models.channel import Channel
        from conda.models.match_spec import MatchSpec

        solver_backend = context.plugin_manager.get_cached_solver_backend()
        if solver_backend is None:
            raise SolverNotAvailableError

        final_prefix = self._prefix_for(key)
        tmp_prefix = self.envs_dir / f".tmp-{key}-{os.getpid()}"
        self.envs_dir.mkdir(parents=True, exist_ok=True)
        tmp_prefix.mkdir(exist_ok=True)

        channel_objs = [Channel(c) for c in channels]
        match_specs = [MatchSpec(s) for s in specs]

        tool = key.rsplit("--", 1)[0]

        solver = solver_backend(
            str(tmp_prefix),
            channel_objs,
            context.subdirs,
            specs_to_add=match_specs,
        )

        try:
            transaction = solver.solve_for_transaction()
        except (UnsatisfiableError, SystemExit) as exc:
            rm_rf(tmp_prefix)
            raise SolveError(tool, str(exc)) from exc

        try:
            transaction.download_and_extract()
            transaction.execute()
            tmp_prefix.rename(final_prefix)
        except BaseException:
            rm_rf(tmp_prefix)
            raise

        return final_prefix

    def exists(self, key: str) -> bool:
        """Check if a cached environment exists (fast stat-only check)."""
        prefix = self._prefix_for(key)
        return prefix.is_dir() and (prefix / "conda-meta").is_dir()

    def remove(self, key: str) -> None:
        """Remove a cached environment."""
        from conda.core.envs_manager import unregister_env
        from conda.gateways.disk.delete import rm_rf

        prefix = self._prefix_for(key)
        if prefix.exists():
            unregister_env(str(prefix))
            rm_rf(prefix)

    def list_cached(self) -> list[CacheEntry]:
        """Enumerate all cached environments with metadata."""
        from conda.core.prefix_data import PrefixData

        if not self.envs_dir.is_dir():
            return []

        entries = []
        for path in sorted(self.envs_dir.iterdir()):
            if not path.is_dir() or "--" not in path.name:
                continue
            if path.name.startswith(".tmp-"):
                continue
            conda_meta = path / "conda-meta"
            if not conda_meta.is_dir():
                continue

            tool = path.name.rsplit("--", 1)[0]
            pd = PrefixData(path)
            package_count = len(list(conda_meta.glob("*.json")))

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

    def _prefix_for(self, key: str) -> Path:
        if len(key) > MAX_ENV_NAME_LEN:
            raise ValueError(f"cache key too long: {len(key)} > {MAX_ENV_NAME_LEN}")
        if not _SAFE_KEY_RE.match(key):
            raise ValueError(f"invalid cache key: {key!r}")
        prefix = self.envs_dir / key
        resolved = prefix.resolve()
        if not resolved.is_relative_to(self.envs_dir.resolve()):
            raise ValueError(f"cache key escapes envs directory: {key!r}")
        return prefix

    def _touch(self, prefix: Path) -> None:
        """Update the history file mtime for staleness tracking."""
        try:
            os.utime(prefix / "conda-meta" / "history")
        except FileNotFoundError:
            pass
