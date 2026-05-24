"""Shared test fixtures for conda-exec."""

from __future__ import annotations

import stat
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda_exec.cache import CacheEntry
from conda_exec.cli import configure_parser

pytest_plugins = ["conda.testing.fixtures"]

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


@pytest.fixture()
def exec_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    """Set CONDA_EXEC_HOME to a temp directory and clear caches."""
    home = tmp_path / "conda-exec"
    home.mkdir()
    monkeypatch.setenv("CONDA_EXEC_HOME", str(home))

    from conda_exec.paths import data_dir

    data_dir.cache_clear()
    yield home
    data_dir.cache_clear()


@pytest.fixture()
def prefix(tmp_path: Path) -> Path:
    """Create a conda prefix with bin/ and conda-meta/."""
    p = tmp_path / "envs" / "test-tool--abcd1234"
    (p / "conda-meta").mkdir(parents=True)
    (p / "bin").mkdir()
    return p


@pytest.fixture()
def binary(prefix: Path) -> Path:
    """Create an executable in a prefix's bin/."""
    b = prefix / "bin" / "mytool"
    b.write_text("#!/bin/sh\nexit 0\n")
    b.chmod(b.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return b


@pytest.fixture()
def executable() -> Callable[[Path], None]:
    """Factory that marks a path as an executable script."""

    def _chmod(path: Path) -> None:
        path.write_text("#!/bin/sh\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return _chmod


@pytest.fixture()
def solver_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Replace CacheManager.create with a stub that records calls."""
    calls: list[dict] = []

    def _create(self, key, specs, channels):
        p = self.envs_dir / key
        p.mkdir(parents=True, exist_ok=True)
        (p / "conda-meta").mkdir(exist_ok=True)
        (p / "conda-meta" / "history").touch()
        calls.append({"key": key, "specs": specs, "channels": channels})
        return p

    monkeypatch.setattr("conda_exec.cache.CacheManager.create", _create)
    return calls


@pytest.fixture()
def parser() -> ArgumentParser:
    """Create the top-level ``conda exec`` argument parser."""
    p = ArgumentParser()
    configure_parser(p)
    return p


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
