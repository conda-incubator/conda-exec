"""Shared test fixtures for conda-exec."""

from __future__ import annotations

import stat
import tempfile
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from conda.common.compat import on_win
from conda.common.path import BIN_DIRECTORY

from conda_exec.cache import CacheEntry
from conda_exec.cli import configure_parser

pytest_plugins = ["conda.testing.fixtures"]

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


@pytest.fixture
def exec_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    """Set CONDA_EXEC_HOME to a temp directory and clear caches."""
    home = tmp_path / "conda-exec"
    home.mkdir()
    monkeypatch.setenv("CONDA_EXEC_HOME", str(home))

    from conda_exec.paths import data_dir

    data_dir.cache_clear()
    yield home
    data_dir.cache_clear()


@pytest.fixture
def prefix(tmp_path: Path) -> Path:
    """Create a conda prefix with the platform-correct bin dir and conda-meta/."""
    env_prefix = tmp_path / "envs" / "test-tool--abcd1234"
    (env_prefix / "conda-meta").mkdir(parents=True)
    (env_prefix / BIN_DIRECTORY).mkdir()
    return env_prefix


@pytest.fixture
def binary(prefix: Path) -> Path:
    """Create an executable in a prefix's bin dir."""
    if on_win:
        tool_bin = prefix / BIN_DIRECTORY / "mytool.exe"
        tool_bin.write_text("")
    else:
        tool_bin = prefix / BIN_DIRECTORY / "mytool"
        tool_bin.write_text("#!/bin/sh\nexit 0\n")
        tool_bin.chmod(
            tool_bin.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
    return tool_bin


@pytest.fixture
def executable() -> Callable[[Path], None]:
    """Factory that marks a path executable (or creates a .exe on Windows)."""

    def make_executable(path: Path) -> None:
        if on_win:
            path = path.with_suffix(".exe") if not path.suffix else path
            path.write_text("")
        else:
            path.write_text("#!/bin/sh\n")
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return make_executable


@pytest.fixture
def solver_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Replace CacheManager.create with a stub that records calls."""
    calls: list[dict] = []

    def create_env(self, key, specs, channels):
        env_prefix = self.envs_dir / key
        env_prefix.mkdir(parents=True, exist_ok=True)
        (env_prefix / "conda-meta").mkdir(exist_ok=True)
        (env_prefix / "conda-meta" / "history").touch()
        (env_prefix / BIN_DIRECTORY).mkdir(exist_ok=True)
        calls.append({"key": key, "specs": specs, "channels": channels})
        return env_prefix

    monkeypatch.setattr("conda_exec.cache.CacheManager.create", create_env)
    return calls


@pytest.fixture
def parser() -> ArgumentParser:
    """Create the top-level ``conda exec`` argument parser."""
    arg_parser = ArgumentParser()
    configure_parser(arg_parser)
    return arg_parser


@pytest.fixture
def write_script(tmp_path: Path) -> Callable[..., Path]:
    """Factory that writes a script file and returns its path."""

    def write_file(content: str, name: str = "test_script.py") -> Path:
        script = tmp_path / name
        script.write_text(content)
        return script

    return write_file


@pytest.fixture
def script_env(
    exec_home: Path,
    solver_calls: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> list[dict]:
    """Isolated script execution environment.

    Patches find_python to create a fake python binary and
    run_in_prefix to return 0. Returns solver_calls for assertions.
    """
    python_name = "python.exe" if on_win else "python"
    python_short_path = python_name if on_win else f"bin/{python_name}"

    def fake_find_python(prefix: Path) -> Path | None:
        python = prefix / python_short_path
        python.parent.mkdir(parents=True, exist_ok=True)
        if on_win:
            python.write_text("")
        else:
            python.write_text("#!/bin/sh\n")
            python.chmod(
                python.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
        return python

    monkeypatch.setattr("conda_exec.binaries.find_python", fake_find_python)
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix", lambda prefix, binary, args, **kw: 0
    )
    return solver_calls


@pytest.fixture
def cache_entry() -> Callable[..., CacheEntry]:
    """Factory fixture that builds CacheEntry instances."""

    def build_entry(
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
            prefix=Path(tempfile.gettempdir()) / "envs" / key,
            created=now - timedelta(days=age_days + 1),
            last_modified=now - timedelta(days=age_days),
            size=size,
            package_count=package_count,
        )

    return build_entry
