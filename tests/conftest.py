"""Shared test fixtures for conda-exec."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def mock_exec_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set CONDA_EXEC_HOME to a temp directory and clear caches."""
    exec_home = tmp_path / "conda-exec"
    exec_home.mkdir()
    monkeypatch.setenv("CONDA_EXEC_HOME", str(exec_home))

    from conda_exec.paths import data_dir

    data_dir.cache_clear()
    yield exec_home
    data_dir.cache_clear()


@pytest.fixture()
def fake_prefix(tmp_path: Path) -> Path:
    """Create a fake conda prefix with bin/ and conda-meta/."""
    prefix = tmp_path / "envs" / "test-tool--abcd1234"
    (prefix / "conda-meta").mkdir(parents=True)
    (prefix / "bin").mkdir()
    return prefix


@pytest.fixture()
def fake_binary(fake_prefix: Path) -> Path:
    """Create a fake executable in a prefix's bin/."""
    binary = fake_prefix / "bin" / "mytool"
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return binary


@pytest.fixture()
def solver_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Replace CacheManager.create with a fake that records calls."""
    calls: list[dict] = []

    def fake_create(self, key, specs, channels):
        prefix = self.envs_dir / key
        prefix.mkdir(parents=True, exist_ok=True)
        (prefix / "conda-meta").mkdir(exist_ok=True)
        (prefix / "conda-meta" / "history").touch()
        calls.append({"key": key, "specs": specs, "channels": channels})
        return prefix

    monkeypatch.setattr("conda_exec.cache.CacheManager.create", fake_create)
    return calls
