"""Tests for conda_exec.cli.main."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conda_exec.cache import CacheEntry
from conda_exec.cli.main import (
    configure_clean_parser,
    configure_list_parser,
    configure_parser,
    execute,
    execute_clean,
    execute_list,
    format_age,
    format_size,
)


@pytest.fixture()
def parser() -> ArgumentParser:
    p = ArgumentParser()
    configure_parser(p)
    return p


# ---------------------------------------------------------------------------
# Argument parsing -- exec (tool execution)
# ---------------------------------------------------------------------------


def test_parse_bare_tool(parser: ArgumentParser):
    args = parser.parse_args(["ruff"])
    assert args.tool == "ruff"
    assert args.tool_args == []
    assert args.channels is None
    assert args.spec is None
    assert args.with_specs is None


def test_parse_tool_with_args(parser: ArgumentParser):
    args = parser.parse_args(["ruff", "check", "."])
    assert args.tool == "ruff"
    assert args.tool_args == ["check", "."]


def test_parse_tool_with_separator(parser: ArgumentParser):
    args = parser.parse_args(["ruff", "--", "--check", "."])
    assert args.tool == "ruff"
    assert args.tool_args == ["--check", "."]


def test_parse_channel(parser: ArgumentParser):
    args = parser.parse_args(["-c", "bioconda", "samtools"])
    assert args.channels == ["bioconda"]
    assert args.tool == "samtools"


def test_parse_multiple_channels(parser: ArgumentParser):
    args = parser.parse_args(["-c", "bioconda", "-c", "defaults", "samtools"])
    assert args.channels == ["bioconda", "defaults"]


def test_parse_spec(parser: ArgumentParser):
    args = parser.parse_args(["--spec", "ruff>=0.4", "ruff"])
    assert args.spec == "ruff>=0.4"
    assert args.tool == "ruff"


def test_parse_with_specs(parser: ArgumentParser):
    args = parser.parse_args(["--with", "pytest", "--with", "python=3.12", "ruff"])
    assert args.with_specs == ["pytest", "python=3.12"]
    assert args.tool == "ruff"


def test_parse_refresh(parser: ArgumentParser):
    args = parser.parse_args(["--refresh", "ruff"])
    assert args.refresh is True


def test_parse_no_refresh_default(parser: ArgumentParser):
    args = parser.parse_args(["ruff"])
    assert args.refresh is False


def test_parse_all_options(parser: ArgumentParser):
    args = parser.parse_args(
        [
            "-c",
            "bioconda",
            "--spec",
            "ruff>=0.4",
            "--with",
            "pytest",
            "--refresh",
            "ruff",
            "check",
            ".",
        ]
    )
    assert args.channels == ["bioconda"]
    assert args.spec == "ruff>=0.4"
    assert args.with_specs == ["pytest"]
    assert args.refresh is True
    assert args.tool == "ruff"
    assert args.tool_args == ["check", "."]


# ---------------------------------------------------------------------------
# Argument parsing -- list and clean as tool names
# ---------------------------------------------------------------------------


def test_parse_list_as_tool(parser: ArgumentParser):
    args = parser.parse_args(["list"])
    assert args.tool == "list"
    assert args.tool_args == []


def test_parse_list_json_as_tool_args(parser: ArgumentParser):
    args = parser.parse_args(["list", "--json"])
    assert args.tool == "list"
    assert args.tool_args == ["--json"]


def test_parse_clean_as_tool(parser: ArgumentParser):
    args = parser.parse_args(["clean"])
    assert args.tool == "clean"
    assert args.tool_args == []


def test_parse_clean_all_as_tool_args(parser: ArgumentParser):
    args = parser.parse_args(["clean", "--all"])
    assert args.tool == "clean"
    assert args.tool_args == ["--all"]


def test_parse_clean_with_options_as_tool_args(parser: ArgumentParser):
    args = parser.parse_args(["clean", "--all", "--dry-run", "ruff"])
    assert args.tool == "clean"
    assert args.tool_args == ["--all", "--dry-run", "ruff"]


# ---------------------------------------------------------------------------
# Subcommand-specific parsers
# ---------------------------------------------------------------------------


def test_list_parser_defaults():
    p = ArgumentParser()
    configure_list_parser(p)
    args = p.parse_args([])
    assert args.json_output is False


def test_list_parser_json():
    p = ArgumentParser()
    configure_list_parser(p)
    args = p.parse_args(["--json"])
    assert args.json_output is True


def test_clean_parser_defaults():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args([])
    assert args.remove_all is False
    assert args.older_than == 30
    assert args.dry_run is False
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


def test_clean_parser_tool():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["ruff"])
    assert args.tool == "ruff"


def test_clean_parser_all_options():
    p = ArgumentParser()
    configure_clean_parser(p)
    args = p.parse_args(["--all", "--dry-run", "--older-than", "7", "ruff"])
    assert args.remove_all is True
    assert args.dry_run is True
    assert args.older_than == 7
    assert args.tool == "ruff"


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_dispatch_to_list(parser: ArgumentParser, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cli.main.execute_list", lambda args: (calls.append("list"), 0)[1]
    )
    args = parser.parse_args(["list"])
    rc = execute(args, parser)
    assert rc == 0
    assert calls == ["list"]


def test_dispatch_to_clean(parser: ArgumentParser, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cli.main.execute_clean",
        lambda args: (calls.append("clean"), 0)[1],
    )
    args = parser.parse_args(["clean"])
    rc = execute(args, parser)
    assert rc == 0
    assert calls == ["clean"]


def test_dispatch_to_run(parser: ArgumentParser, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cli.main.execute_run", lambda args: (calls.append("run"), 0)[1]
    )
    args = parser.parse_args(["ruff"])
    rc = execute(args, parser)
    assert rc == 0
    assert calls == ["run"]


def test_dispatch_list_parses_subcommand_args(
    parser: ArgumentParser, monkeypatch: pytest.MonkeyPatch
):
    received_args: list = []
    monkeypatch.setattr(
        "conda_exec.cli.main.execute_list",
        lambda args: (received_args.append(args), 0)[1],
    )
    args = parser.parse_args(["list", "--json"])
    execute(args, parser)
    assert received_args[0].json_output is True


def test_dispatch_clean_parses_subcommand_args(
    parser: ArgumentParser, monkeypatch: pytest.MonkeyPatch
):
    received_args: list = []
    monkeypatch.setattr(
        "conda_exec.cli.main.execute_clean",
        lambda args: (received_args.append(args), 0)[1],
    )
    args = parser.parse_args(["clean", "--all", "--dry-run", "ruff"])
    execute(args, parser)
    assert received_args[0].remove_all is True
    assert received_args[0].dry_run is True
    assert received_args[0].tool == "ruff"


# ---------------------------------------------------------------------------
# format_size
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("size_bytes", "expected"),
    [
        (0, "0 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
        (1073741824, "1.0 GB"),
        (1099511627776, "1.0 TB"),
    ],
    ids=[
        "zero",
        "bytes-mid",
        "bytes-max",
        "one-kb",
        "fractional-kb",
        "one-mb",
        "one-gb",
        "one-tb",
    ],
)
def test_format_size(size_bytes: int, expected: str):
    assert format_size(size_bytes) == expected


# ---------------------------------------------------------------------------
# format_age
# ---------------------------------------------------------------------------


def test_format_age_none():
    assert format_age(None) == "unknown"


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (timedelta(seconds=10), "just now"),
        (timedelta(seconds=90), "1 minute ago"),
        (timedelta(minutes=15), "15 minutes ago"),
        (timedelta(hours=1), "1 hour ago"),
        (timedelta(hours=5), "5 hours ago"),
        (timedelta(days=1), "1 day ago"),
        (timedelta(days=42), "42 days ago"),
    ],
    ids=[
        "just-now",
        "one-minute",
        "minutes",
        "one-hour",
        "hours",
        "one-day",
        "days",
    ],
)
def test_format_age(delta: timedelta, expected: str):
    dt = datetime.now(tz=timezone.utc) - delta
    assert format_age(dt) == expected


def test_format_age_naive_datetime():
    dt = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=3)
    assert format_age(dt) == "3 days ago"


# ---------------------------------------------------------------------------
# execute_list
# ---------------------------------------------------------------------------


def _make_entry(
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
        prefix=Path(f"/fake/envs/{key}"),
        created=now - timedelta(days=age_days + 1),
        last_modified=now - timedelta(days=age_days),
        size=size,
        package_count=package_count,
    )


def test_execute_list_empty(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("conda_exec.cache.CacheManager.list_cached", lambda self: [])
    p = ArgumentParser()
    configure_list_parser(p)
    args = p.parse_args([])
    rc = execute_list(args)
    assert rc == 0
    assert "No cached environments." in capsys.readouterr().out


def test_execute_list_table(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    entries = [
        _make_entry(
            tool="ruff", key="ruff--abcd1234", size=45_000_000, package_count=3
        ),
        _make_entry(
            tool="samtools",
            key="samtools--ef567890",
            size=120_000_000,
            package_count=47,
            age_days=3,
        ),
    ]
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    p = ArgumentParser()
    configure_list_parser(p)
    args = p.parse_args([])
    rc = execute_list(args)
    assert rc == 0

    output = capsys.readouterr().out
    assert "Tool" in output
    assert "ruff" in output
    assert "samtools" in output
    assert "42.9 MB" in output
    assert "114.4 MB" in output


def test_execute_list_json(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    entries = [
        _make_entry(tool="ruff", key="ruff--abcd1234"),
    ]
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.list_cached", lambda self: entries
    )
    p = ArgumentParser()
    configure_list_parser(p)
    args = p.parse_args(["--json"])
    rc = execute_list(args)
    assert rc == 0

    output = capsys.readouterr().out
    data = json.loads(output)
    assert len(data) == 1
    assert data[0]["tool"] == "ruff"
    assert data[0]["key"] == "ruff--abcd1234"
    assert data[0]["size_bytes"] == 45_000_000
    assert data[0]["packages"] == 3
    assert data[0]["created"] is not None
    assert data[0]["last_used"] is not None


# ---------------------------------------------------------------------------
# execute_clean
# ---------------------------------------------------------------------------


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


def test_execute_clean_all(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    entries = [
        _make_entry(tool="ruff", key="ruff--abcd1234"),
        _make_entry(tool="samtools", key="samtools--ef567890"),
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
    args = p.parse_args(["--all"])
    rc = execute_clean(args)
    assert rc == 0
    assert sorted(removed) == ["ruff--abcd1234", "samtools--ef567890"]

    output = capsys.readouterr().out
    assert "Cleaned 2 environment(s)" in output


def test_execute_clean_older_than(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    entries = [
        _make_entry(tool="ruff", key="ruff--abcd1234", age_days=2),
        _make_entry(tool="samtools", key="samtools--ef567890", age_days=40),
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
    args = p.parse_args(["--older-than", "30"])
    rc = execute_clean(args)
    assert rc == 0
    assert removed == ["samtools--ef567890"]


def test_execute_clean_tool_filter(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    entries = [
        _make_entry(tool="ruff", key="ruff--abcd1234", age_days=40),
        _make_entry(tool="samtools", key="samtools--ef567890", age_days=40),
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
    args = p.parse_args(["ruff"])
    rc = execute_clean(args)
    assert rc == 0
    assert removed == ["ruff--abcd1234"]


def test_execute_clean_dry_run(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    entries = [
        _make_entry(tool="ruff", key="ruff--abcd1234", age_days=40),
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
):
    entries = [
        _make_entry(tool="ruff", key="ruff--abcd1234", age_days=2),
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
):
    entries = [
        _make_entry(tool="ruff", key="ruff--abcd1234"),
        _make_entry(tool="ruff", key="ruff--beef9876"),
        _make_entry(tool="samtools", key="samtools--ef567890"),
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
    args = p.parse_args(["--all", "ruff"])
    rc = execute_clean(args)
    assert rc == 0
    assert sorted(removed) == ["ruff--abcd1234", "ruff--beef9876"]
    assert "samtools--ef567890" not in removed
