"""Tests for conda_exec.binaries."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from conda_exec.binaries import discover_binaries, find_binary


@pytest.fixture()
def unix_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("conda_exec.binaries.BIN_DIRECTORY", "bin")
    monkeypatch.setattr("conda.base.constants.on_win", False)
    prefix = tmp_path / "env"
    (prefix / "bin").mkdir(parents=True)
    return prefix


@pytest.fixture()
def win_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("conda_exec.binaries.BIN_DIRECTORY", "Scripts")
    monkeypatch.setattr("conda.base.constants.on_win", True)
    prefix = tmp_path / "env"
    (prefix / "Scripts").mkdir(parents=True)
    return prefix


def _make_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_find_binary_unix(unix_prefix: Path):
    _make_executable(unix_prefix / "bin" / "ruff")
    result = find_binary(unix_prefix, "ruff")
    assert result is not None
    assert result.name == "ruff"


def test_find_binary_unix_missing(unix_prefix: Path):
    assert find_binary(unix_prefix, "nonexistent") is None


def test_find_binary_no_bin_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda_exec.binaries.BIN_DIRECTORY", "bin")
    monkeypatch.setattr("conda.base.constants.on_win", False)
    assert find_binary(tmp_path, "ruff") is None


@pytest.mark.parametrize("ext", [".exe", ".bat", ".cmd"])
def test_find_binary_windows(win_prefix: Path, ext: str):
    (win_prefix / "Scripts" / f"ruff{ext}").write_text("")
    result = find_binary(win_prefix, "ruff")
    assert result is not None
    assert result.stem == "ruff"


def test_discover_binaries_unix(unix_prefix: Path):
    _make_executable(unix_prefix / "bin" / "alpha")
    _make_executable(unix_prefix / "bin" / "beta")
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
    monkeypatch.setattr("conda.base.constants.on_win", False)
    assert discover_binaries(tmp_path) == []
