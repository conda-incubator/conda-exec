"""Shared fixtures for CLI tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda_exec.cache import CacheEntry

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture()
def cache_entry() -> Callable[..., CacheEntry]:
    """Factory fixture that builds CacheEntry instances."""

    def _build(
        tool: str = "ruff",
        key: str = "ruff--abcd1234",
        size: int = 45_000_000,
        package_count: int = 3,
        age_days: int = 0,
    ) -> CacheEntry:
        now = datetime.now(tz=timezone.utc)
        return CacheEntry(
            key=key,
            tool=tool,
            prefix=Path(f"/tmp/envs/{key}"),
            created=now - timedelta(days=age_days + 1),
            last_modified=now - timedelta(days=age_days),
            size=size,
            package_count=package_count,
        )

    return _build
