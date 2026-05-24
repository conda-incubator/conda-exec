"""Tests for conda_exec.cli.clean -- clean command."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from conda_exec.cache import CacheEntry
from conda_exec.cli.clean import configure_clean_parser, execute_clean

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest


def test_clean_parser_defaults():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args([])
    assert args.remove_all is False
    assert args.older_than == 30
    assert args.dry_run is False
    assert args.yes is False
    assert args.tool is None


def test_clean_parser_all():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--all"])
    assert args.remove_all is True


def test_clean_parser_older_than():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--older-than", "7"])
    assert args.older_than == 7


def test_clean_parser_dry_run():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--dry-run"])
    assert args.dry_run is True


def test_clean_parser_yes():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--yes"])
    assert args.yes is True


def test_clean_parser_yes_short():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["-y"])
    assert args.yes is True


def test_clean_parser_tool():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["ruff"])
    assert args.tool == "ruff"


def test_clean_parser_all_options():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--all", "--dry-run", "--older-than", "7", "-y", "ruff"])
    assert args.remove_all is True
    assert args.dry_run is True
    assert args.older_than == 7
    assert args.yes is True
    assert args.tool == "ruff"


def test_execute_clean_empty(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("conda_exec.cache.CacheManager.list_cached", lambda self: [])
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args([])
    rc = execute_clean(args)
    assert rc == 0
    assert "No cached environments to clean." in capsys.readouterr().out


def test_execute_clean_all_with_yes(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234"),
        cache_entry(tool="samtools", key="samtools--ef567890"),
    ]
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--all", "--yes"])
    rc = execute_clean(args)
    assert rc == 0
    assert sorted(removed) == ["ruff--abcd1234", "samtools--ef567890"]

    output = capsys.readouterr().out
    assert "Cleaned 2 environment(s)" in output


def test_execute_clean_older_than_with_yes(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234", age_days=2),
        cache_entry(tool="samtools", key="samtools--ef567890", age_days=40),
    ]
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--older-than", "30", "--yes"])
    rc = execute_clean(args)
    assert rc == 0
    assert removed == ["samtools--ef567890"]


def test_execute_clean_tool_filter_with_yes(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234", age_days=40),
        cache_entry(tool="samtools", key="samtools--ef567890", age_days=40),
    ]
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--yes", "ruff"])
    rc = execute_clean(args)
    assert rc == 0
    assert removed == ["ruff--abcd1234"]


def test_execute_clean_dry_run(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234", age_days=40),
    ]
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--dry-run"])
    rc = execute_clean(args)
    assert rc == 0
    assert removed == []

    output = capsys.readouterr().out
    assert "Would remove 1 environment(s)" in output
    assert "ruff--abcd1234" in output


def test_execute_clean_nothing_matches(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234", age_days=2),
    ]
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--older-than", "30"])
    rc = execute_clean(args)
    assert rc == 0
    assert "Nothing to clean." in capsys.readouterr().out


def test_execute_clean_all_with_tool_filter(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234"),
        cache_entry(tool="ruff", key="ruff--beef9876"),
        cache_entry(tool="samtools", key="samtools--ef567890"),
    ]
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--all", "--yes", "ruff"])
    rc = execute_clean(args)
    assert rc == 0
    assert sorted(removed) == ["ruff--abcd1234", "ruff--beef9876"]
    assert "samtools--ef567890" not in removed


def test_execute_clean_skips_entry_without_last_modified(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime.now(tz=timezone.utc)
    entry = CacheEntry(
        key="ruff--abcd1234",
        tool="ruff",
        prefix=Path("/fake/envs/ruff--abcd1234"),
        created=now - timedelta(days=100),
        last_modified=None,
        size=45_000_000,
        package_count=3,
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: [entry]
    )
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--older-than", "30"])
    rc = execute_clean(args)
    assert rc == 0
    assert "Nothing to clean." in capsys.readouterr().out


def test_execute_clean_prompts_without_yes(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234", age_days=40),
    ]
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )
    monkeypatch.setattr("conda.reporters.confirm_yn", lambda *a, **kw: True)
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args([])
    rc = execute_clean(args)
    assert rc == 0
    assert removed == ["ruff--abcd1234"]

    output = capsys.readouterr().out
    assert "Will remove 1 environment(s)" in output


def test_execute_clean_prompt_declined(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    from conda.exceptions import CondaSystemExit

    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234", age_days=40),
    ]
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )

    def decline(*a, **kw):
        raise CondaSystemExit("Exiting.")

    monkeypatch.setattr("conda.reporters.confirm_yn", decline)
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args([])
    rc = execute_clean(args)
    assert rc == 1
    assert removed == []
    assert "Aborted." in capsys.readouterr().out


def test_execute_clean_prompt_eof(
    monkeypatch: pytest.MonkeyPatch,
    cache_entry: Callable[..., CacheEntry],
):
    entries = [
        cache_entry(tool="ruff", key="ruff--abcd1234", age_days=40),
    ]
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )

    def raise_eof(*a, **kw):
        raise EOFError

    monkeypatch.setattr("conda.reporters.confirm_yn", raise_eof)
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args([])
    rc = execute_clean(args)
    assert rc == 1
