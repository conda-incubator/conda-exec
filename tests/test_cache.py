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

    prefix1, created1 = cm.get_or_create(key, ["ruff"], ["conda-forge"])
    assert created1 is True
    assert len(solver_calls) == 1

    prefix2, created2 = cm.get_or_create(key, ["ruff"], ["conda-forge"])
    assert created2 is False
    assert len(solver_calls) == 1
    assert prefix1 == prefix2


def test_get_or_create_creates_on_miss(
    exec_home: Path,
    solver_calls: list[dict],
):
    cm = CacheManager()
    prefix, created = cm.get_or_create("ruff--abcdef01", ["ruff"], ["conda-forge"])
    assert created is True
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
    import os

    prefix = tmp_path / "envs" / "ruff--abcd1234"
    (prefix / "conda-meta").mkdir(parents=True)
    history = prefix / "conda-meta" / "history"
    history.write_text("initial\n")

    old_time = 1_000_000.0
    os.utime(history, (old_time, old_time))

    cm = CacheManager(envs_dir=tmp_path / "envs")
    cm.touch(prefix)

    assert history.stat().st_mtime > old_time


def test_touch_skips_recent(tmp_path: Path):
    prefix = tmp_path / "envs" / "ruff--abcd1234"
    (prefix / "conda-meta").mkdir(parents=True)
    history = prefix / "conda-meta" / "history"
    history.write_text("initial\n")

    mtime_before = history.stat().st_mtime
    cm = CacheManager(envs_dir=tmp_path / "envs")
    cm.touch(prefix)

    assert history.stat().st_mtime == mtime_before


def test_cache_key_too_long(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    long_key = "a" * 201
    with pytest.raises(ValueError, match="cache key too long"):
        cm.prefix_for(long_key)


def test_cache_key_deterministic(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    key1 = cm.cache_key("ruff", ["ruff"], ["conda-forge"])
    key2 = cm.cache_key("ruff", ["ruff"], ["conda-forge"])
    assert key1 == key2


def test_cache_key_starts_with_tool(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    key = cm.cache_key("ruff", ["ruff"], ["conda-forge"])
    assert key.startswith("ruff--")


def test_cache_key_has_hash(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    key = cm.cache_key("ruff", ["ruff"], ["conda-forge"])
    _, h = key.split("--", 1)
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_cache_key_differs_with_different_specs(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    key1 = cm.cache_key("ruff", ["ruff"], ["conda-forge"])
    key2 = cm.cache_key("ruff", ["ruff>=0.4"], ["conda-forge"])
    assert key1 != key2


def test_cache_key_differs_with_different_channels(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    key1 = cm.cache_key("ruff", ["ruff"], ["conda-forge"])
    key2 = cm.cache_key("ruff", ["ruff"], ["defaults"])
    assert key1 != key2


def test_cache_key_order_independent(tmp_path: Path):
    cm = CacheManager(envs_dir=tmp_path)
    key1 = cm.cache_key("ruff", ["ruff", "pytest"], ["conda-forge"])
    key2 = cm.cache_key("ruff", ["pytest", "ruff"], ["conda-forge"])
    assert key1 == key2


@pytest.mark.parametrize(
    ("name", "match"),
    [
        ("", "cannot be empty"),
        ("a" * 129, "too long"),
        ("ruff@evil", "invalid tool name"),
        ("../escape", "invalid tool name"),
    ],
    ids=["empty", "too-long", "special-chars", "path-traversal"],
)
def test_cache_key_rejects_invalid_tool_name(tmp_path: Path, name: str, match: str):
    cm = CacheManager(envs_dir=tmp_path)
    with pytest.raises(ValueError, match=match):
        cm.cache_key(name, [name], ["conda-forge"])
