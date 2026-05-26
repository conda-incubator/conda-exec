"""Tests for conda_exec.cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda_exec.cache import CacheManager
from conda_exec.exceptions import SolveError, SolverNotAvailableError

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


def test_create_no_solver_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "conda.base.context.context.plugin_manager.get_cached_solver_backend",
        lambda name=None: None,
    )
    cm = CacheManager(envs_dir=tmp_path)
    with pytest.raises(SolverNotAvailableError):
        cm.create("ruff--abcd1234", ["ruff"], ["conda-forge"])


def test_create_solve_failure_cleans_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from conda.exceptions import PackagesNotFoundError

    class FailingSolver:
        def __init__(self, *args, **kwargs):
            pass

        def solve_for_transaction(self):
            raise PackagesNotFoundError(["ruff"])

    monkeypatch.setattr(
        "conda.base.context.context.plugin_manager.get_cached_solver_backend",
        lambda name=None: FailingSolver,
    )
    cm = CacheManager(envs_dir=tmp_path)
    with pytest.raises(SolveError, match="ruff"):
        cm.create("ruff--abcd1234", ["ruff"], ["conda-forge"])

    remaining = [p for p in tmp_path.iterdir() if p.name.startswith(".tmp-")]
    assert remaining == []


def test_create_invalid_match_spec_cleans_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class FakeSolver:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(
        "conda.base.context.context.plugin_manager.get_cached_solver_backend",
        lambda name=None: FakeSolver,
    )
    cm = CacheManager(envs_dir=tmp_path)
    with pytest.raises(SolveError, match="ruff"):
        cm.create("ruff--abcd1234", ["../ruff"], ["conda-forge"])

    remaining = [p for p in tmp_path.iterdir() if p.name.startswith(".tmp-")]
    assert remaining == []


def test_create_atomic_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    class FakeTransaction:
        def download_and_extract(self):
            pass

        def execute(self):
            pass

    class FakeSolver:
        def __init__(self, *args, **kwargs):
            pass

        def solve_for_transaction(self):
            return FakeTransaction()

    monkeypatch.setattr(
        "conda.base.context.context.plugin_manager.get_cached_solver_backend",
        lambda name=None: FakeSolver,
    )
    cm = CacheManager(envs_dir=tmp_path)
    prefix = cm.create("ruff--abcd1234", ["ruff"], ["conda-forge"])

    assert prefix == tmp_path / "ruff--abcd1234"
    assert prefix.is_dir()
    remaining_tmp = [p for p in tmp_path.iterdir() if p.name.startswith(".tmp-")]
    assert remaining_tmp == []


def test_create_concurrent_race(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    final_prefix = tmp_path / "ruff--abcd1234"
    (final_prefix / "conda-meta").mkdir(parents=True)

    class FakeTransaction:
        def download_and_extract(self):
            pass

        def execute(self):
            pass

    class FakeSolver:
        def __init__(self, *args, **kwargs):
            pass

        def solve_for_transaction(self):
            return FakeTransaction()

    monkeypatch.setattr(
        "conda.base.context.context.plugin_manager.get_cached_solver_backend",
        lambda name=None: FakeSolver,
    )
    cm = CacheManager(envs_dir=tmp_path)
    prefix = cm.create("ruff--abcd1234", ["ruff"], ["conda-forge"])

    assert prefix == final_prefix
    remaining_tmp = [p for p in tmp_path.iterdir() if p.name.startswith(".tmp-")]
    assert remaining_tmp == []


def test_remove_deletes_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    prefix = tmp_path / "ruff--abcd1234"
    (prefix / "conda-meta").mkdir(parents=True)
    (prefix / "conda-meta" / "history").write_text("init\n")

    monkeypatch.setattr("conda.core.envs_manager.unregister_env", lambda path: None)
    monkeypatch.setattr("conda.core.prefix_data.PrefixData._cache_", {})

    cm = CacheManager(envs_dir=tmp_path)
    cm.remove("ruff--abcd1234")

    assert not prefix.exists()


def test_list_cached_with_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for name in ["ruff--aaa11111", "samtools--bbb22222", ".tmp-stale"]:
        entry = tmp_path / name
        entry.mkdir()
        if not name.startswith(".tmp-"):
            meta = entry / "conda-meta"
            meta.mkdir()
            (meta / "history").write_text("init\n")

    (tmp_path / "no-separator").mkdir()

    class FakePrefixData:
        def __init__(self, path):
            self.path = path

        def is_environment(self):
            return (self.path / "conda-meta" / "history").is_file()

        @property
        def created(self):
            return None

        @property
        def last_modified(self):
            return None

        def size(self):
            return 0

        def iter_records(self):
            return []

    monkeypatch.setattr("conda.core.prefix_data.PrefixData", FakePrefixData)

    cm = CacheManager(envs_dir=tmp_path)
    entries = cm.list_cached()

    tools = [entry.tool for entry in entries]
    assert "ruff" in tools
    assert "samtools" in tools
    assert len(entries) == 2
