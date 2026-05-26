"""Tests for automatic cache cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda_exec.auto_clean import (
    auto_clean_after_success,
    increment_run_count,
    read_run_count,
    write_run_count,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest

    from conda_exec.cache import CacheEntry


def test_run_count_roundtrip(tmp_path: Path):
    path = tmp_path / "run-count"

    assert read_run_count(path) == 0
    assert increment_run_count(path) == 1
    assert read_run_count(path) == 1

    write_run_count(path, 7)

    assert read_run_count(path) == 7


def test_run_count_treats_corrupt_file_as_zero(tmp_path: Path):
    path = tmp_path / "run-count"
    path.write_text("not an int")

    assert increment_run_count(path) == 1
    assert path.read_text() == "1\n"


def test_auto_clean_waits_until_interval(
    exec_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
    capsys: pytest.CaptureFixture,
):
    entries = [cache_entry(tool="ruff", key="ruff--abcd1234", age_days=40)]
    list_calls = []
    removed: list[str] = []

    monkeypatch.setenv("CONDA_EXEC_AUTO_CLEAN", "true")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_INTERVAL", "2")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_AGE", "30")
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached",
        lambda self: (list_calls.append(True), entries)[1],
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )

    auto_clean_after_success()

    assert list_calls == []
    assert removed == []
    assert (exec_home / "run-count").read_text() == "1\n"
    assert capsys.readouterr().err == ""

    auto_clean_after_success()

    assert list_calls == [True]
    assert removed == ["ruff--abcd1234"]
    assert (exec_home / "run-count").read_text() == "0\n"
    assert "cleaned 1 unused environment(s)" in capsys.readouterr().err


def test_auto_clean_disabled_does_not_increment_counter(
    exec_home: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CONDA_EXEC_AUTO_CLEAN", "false")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_INTERVAL", "1")

    auto_clean_after_success()

    assert not (exec_home / "run-count").exists()


def test_auto_clean_silent_when_nothing_removed(
    exec_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
    capsys: pytest.CaptureFixture,
):
    entries = [cache_entry(tool="ruff", key="ruff--abcd1234", age_days=1)]
    removed: list[str] = []

    monkeypatch.setenv("CONDA_EXEC_AUTO_CLEAN", "true")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_INTERVAL", "1")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_AGE", "30")
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached",
        lambda self: entries,
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )

    auto_clean_after_success()

    assert removed == []
    assert (exec_home / "run-count").read_text() == "0\n"
    assert capsys.readouterr().err == ""
