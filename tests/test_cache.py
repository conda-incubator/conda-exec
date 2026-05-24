"""Tests for conda_exec.cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda_exec.cache import CacheManager

if TYPE_CHECKING:
    from pathlib import Path


def test_cache_manager_default_envs_dir(exec_home: Path):
    cm = CacheManager()
    assert cm.envs_dir == exec_home / "envs"


def test_cache_manager_custom_envs_dir(tmp_path: Path):
    custom = tmp_path / "custom"
    cm = CacheManager(envs_dir=custom)
    assert cm.envs_dir == custom


def test_exists_false_when_empty(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    assert not cm.exists("ruff--abcd1234")


def test_exists_true_when_present(tmp_path: Path):
    envs = tmp_path / "envs"
    prefix = envs / "ruff--abcd1234"
    (prefix / "conda-meta").mkdir(parents=True)
    cm = CacheManager(envs_dir=envs)
    assert cm.exists("ruff--abcd1234")


def test_exists_false_without_conda_meta(tmp_path: Path):
    envs = tmp_path / "envs"
    (envs / "ruff--abcd1234").mkdir(parents=True)
    cm = CacheManager(envs_dir=envs)
    assert not cm.exists("ruff--abcd1234")


def test_remove_nonexistent(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    cm.remove("ruff--abcd1234")


def test_get_or_create_uses_cache(
    exec_home: Path,
    solver_calls: list[dict],
):
    cm = CacheManager()
    key = "ruff--abcdef01"

    prefix1 = cm.get_or_create(key, ["ruff"], ["conda-forge"])
    assert len(solver_calls) == 1

    prefix2 = cm.get_or_create(key, ["ruff"], ["conda-forge"])
    assert len(solver_calls) == 1
    assert prefix1 == prefix2


def test_get_or_create_creates_on_miss(
    exec_home: Path,
    solver_calls: list[dict],
):
    cm = CacheManager()
    prefix = cm.get_or_create("ruff--abcdef01", ["ruff"], ["conda-forge"])
    assert prefix.is_dir()
    assert (prefix / "conda-meta").is_dir()
    assert solver_calls[0]["specs"] == ["ruff"]


def test_list_cached_empty(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    assert cm.list_cached() == []


def test_list_cached_nonexistent_dir(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path / "nonexistent")
    assert cm.list_cached() == []


def test_touch_updates_history_mtime(tmp_path: Path):
    prefix = tmp_path / "envs" / "ruff--abcd1234"
    (prefix / "conda-meta").mkdir(parents=True)
    history = prefix / "conda-meta" / "history"
    history.write_text("initial\n")

    import time

    old_mtime = history.stat().st_mtime
    time.sleep(0.05)

    cm = CacheManager(envs_dir=tmp_path / "envs")
    cm.touch(prefix)

    new_mtime = history.stat().st_mtime
    assert new_mtime > old_mtime


def test_cache_key_too_long(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    long_key = "a" * 201
    with pytest.raises(ValueError, match="cache key too long"):
        cm.prefix_for(long_key)
