"""Tests for conda_exec.binaries."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

from conda_exec.binaries import discover_binaries, find_binary, find_python


@pytest.fixture
def unix_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("conda_exec.binaries.BIN_DIRECTORY", "bin")
    monkeypatch.setattr("conda_exec.binaries.on_win", False)
    env_prefix = tmp_path / "env"
    (env_prefix / "bin").mkdir(parents=True)
    return env_prefix


@pytest.fixture
def win_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("conda_exec.binaries.BIN_DIRECTORY", "Scripts")
    monkeypatch.setattr("conda_exec.binaries.on_win", True)
    env_prefix = tmp_path / "env"
    (env_prefix / "Scripts").mkdir(parents=True)
    return env_prefix


@pytest.mark.skipif(sys.platform == "win32", reason="Unix executable permissions")
def test_find_binary_unix(unix_prefix: Path, executable: Callable[[Path], None]):
    executable(unix_prefix / "bin" / "ruff")
    result = find_binary(unix_prefix, "ruff")
    assert result is not None
    assert result.name == "ruff"


def test_find_binary_unix_missing(unix_prefix: Path):
    assert find_binary(unix_prefix, "nonexistent") is None


def test_find_binary_no_bin_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda_exec.binaries.BIN_DIRECTORY", "bin")
    monkeypatch.setattr("conda_exec.binaries.on_win", False)
    assert find_binary(tmp_path, "ruff") is None


@pytest.mark.parametrize("ext", [".exe", ".bat", ".cmd"])
def test_find_binary_windows(win_prefix: Path, ext: str):
    (win_prefix / "Scripts" / f"ruff{ext}").write_text("")
    result = find_binary(win_prefix, "ruff")
    assert result is not None
    assert result.stem == "ruff"


def test_find_binary_windows_prefers_exe(win_prefix: Path):
    for ext in [".cmd", ".bat", ".exe"]:
        (win_prefix / "Scripts" / f"ruff{ext}").write_text("")

    result = find_binary(win_prefix, "ruff")
    assert result is not None
    assert result.name == "ruff.exe"


def test_find_python_windows_prefix_root(
    win_prefix: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("conda.common.path.get_python_short_path", lambda: "python.exe")
    (win_prefix / "python.exe").write_text("")
    result = find_python(win_prefix)
    assert result is not None
    assert result.name == "python.exe"
    assert result.parent == win_prefix


def test_find_python_unix(unix_prefix: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda.common.path.get_python_short_path", lambda: "bin/python")
    (unix_prefix / "bin" / "python").write_text("#!/bin/sh\n")
    result = find_python(unix_prefix)
    assert result is not None
    assert result.name == "python"
    assert result.parent == unix_prefix / "bin"


@pytest.mark.skipif(sys.platform == "win32", reason="chmod +x is a no-op on Windows")
def test_discover_binaries_unix(unix_prefix: Path, executable: Callable[[Path], None]):
    executable(unix_prefix / "bin" / "alpha")
    executable(unix_prefix / "bin" / "beta")
    (unix_prefix / "bin" / "not-exec").write_text("data")
    result = discover_binaries(unix_prefix)
    assert result == ["alpha", "beta"]


def test_discover_binaries_windows(win_prefix: Path):
    (win_prefix / "Scripts" / "alpha.exe").write_text("")
    (win_prefix / "Scripts" / "beta.bat").write_text("")
    (win_prefix / "Scripts" / "data.txt").write_text("")
    result = discover_binaries(win_prefix)
    assert result == ["alpha", "beta"]


def test_discover_binaries_empty(unix_prefix: Path):
    assert discover_binaries(unix_prefix) == []


def test_discover_binaries_no_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda_exec.binaries.BIN_DIRECTORY", "bin")
    monkeypatch.setattr("conda_exec.binaries.on_win", False)
    assert discover_binaries(tmp_path) == []


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks may need privileges")
def test_find_binary_rejects_symlink_outside_prefix(
    unix_prefix: Path, tmp_path: Path, executable: Callable[[Path], None]
):
    outside_bin = tmp_path / "outside" / "ruff"
    outside_bin.parent.mkdir()
    executable(outside_bin)
    link = unix_prefix / "bin" / "ruff"
    link.symlink_to(outside_bin)
    assert find_binary(unix_prefix, "ruff") is None


def test_is_within_prefix_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from conda_exec.binaries import is_within_prefix

    def broken_resolve(self):
        raise OSError("broken")

    monkeypatch.setattr("pathlib.Path.resolve", broken_resolve)
    assert is_within_prefix(tmp_path / "bin" / "ruff", tmp_path) is False
