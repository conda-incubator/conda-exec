"""Tests for conda_exec.cli -- parser configuration and dispatch."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda_exec.cli import execute
from conda_exec.execute import execute_run

if TYPE_CHECKING:
    from argparse import ArgumentParser


def test_parse_bare_tool(parser: ArgumentParser):
    args = parser.parse_args(["ruff"])
    assert args.tool == "ruff"
    assert args.tool_args == []
    assert args.channels is None
    assert args.with_specs is None


@pytest.mark.parametrize(
    ("argv", "attr", "expected"),
    [
        (["ruff", "check", "."], "tool_args", ["check", "."]),
        (["ruff", "--", "--check", "."], "tool_args", ["--check", "."]),
        (["-c", "bioconda", "samtools"], "channels", ["bioconda"]),
        (["ruff>=0.4"], "tool", "ruff>=0.4"),
        (["--activate", "ruff"], "activate", True),
        (["ruff"], "activate", False),
        (["--refresh", "ruff"], "refresh", True),
        (["ruff"], "refresh", False),
        (["--list"], "list_mode", True),
        (["--list", "--json"], "json_output", True),
        (["--clean"], "clean_mode", True),
        (["--clean", "--all"], "remove_all", True),
        (["--clean", "--older-than", "7"], "older_than", 7),
        (["--clean", "--dry-run"], "dry_run", True),
        (["--clean", "-y"], "yes", True),
        (["--clean", "ruff"], "tool", "ruff"),
    ],
    ids=[
        "tool-with-args",
        "tool-with-separator",
        "channel",
        "matchspec",
        "activate",
        "no-activate-default",
        "refresh",
        "no-refresh-default",
        "list",
        "list-json",
        "clean",
        "clean-all",
        "clean-older-than",
        "clean-dry-run",
        "clean-yes",
        "clean-tool-filter",
    ],
)
def test_parse_flag(
    parser: ArgumentParser,
    argv: list[str],
    attr: str,
    expected: object,
):
    args = parser.parse_args(argv)
    assert getattr(args, attr) == expected


def test_parse_multiple_channels(parser: ArgumentParser):
    args = parser.parse_args(["-c", "bioconda", "-c", "defaults", "samtools"])
    assert args.channels == ["bioconda", "defaults"]


def test_parse_with_specs(parser: ArgumentParser):
    args = parser.parse_args(["--with", "pytest", "--with", "python=3.12", "ruff"])
    assert args.with_specs == ["pytest", "python=3.12"]
    assert args.tool == "ruff"


def test_parse_all_options(parser: ArgumentParser):
    args = parser.parse_args(
        [
            "-c",
            "bioconda",
            "--with",
            "pytest",
            "--activate",
            "--refresh",
            "ruff>=0.4",
            "check",
            ".",
        ]
    )
    assert args.channels == ["bioconda"]
    assert args.with_specs == ["pytest"]
    assert args.activate is True
    assert args.refresh is True
    assert args.tool == "ruff>=0.4"
    assert args.tool_args == ["check", "."]


def test_list_clean_mutually_exclusive(parser: ArgumentParser):
    with pytest.raises(SystemExit):
        parser.parse_args(["--list", "--clean"])


@pytest.mark.parametrize(
    ("argv", "target", "label"),
    [
        (["--list"], "conda_exec.list.execute_list", "list"),
        (["--clean"], "conda_exec.clean.execute_clean", "clean"),
        (["ruff"], "conda_exec.execute.execute_run", "run"),
    ],
    ids=["list", "clean", "run"],
)
def test_dispatch(
    parser: ArgumentParser,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    target: str,
    label: str,
):
    calls: list[str] = []
    monkeypatch.setattr(target, lambda args: (calls.append(label), 0)[1])
    args = parser.parse_args(argv)
    rc = execute(args)
    assert rc == 0
    assert calls == [label]


def test_dispatch_list_passes_json(
    parser: ArgumentParser, monkeypatch: pytest.MonkeyPatch
):
    received_args: list = []
    monkeypatch.setattr(
        "conda_exec.list.execute_list",
        lambda args: (received_args.append(args), 0)[1],
    )
    args = parser.parse_args(["--list", "--json"])
    execute(args)
    assert received_args[0].json_output is True


def test_dispatch_clean_passes_flags(
    parser: ArgumentParser, monkeypatch: pytest.MonkeyPatch
):
    received_args: list = []
    monkeypatch.setattr(
        "conda_exec.clean.execute_clean",
        lambda args: (received_args.append(args), 0)[1],
    )
    args = parser.parse_args(["--clean", "--all", "--dry-run", "ruff"])
    execute(args)
    assert received_args[0].remove_all is True
    assert received_args[0].dry_run is True
    assert received_args[0].tool == "ruff"


def test_execute_run_missing_tool(
    parser: ArgumentParser,
    capsys: pytest.CaptureFixture,
):
    args = parser.parse_args([])
    rc = execute_run(args)
    assert rc == 2
    assert "missing TOOL argument" in capsys.readouterr().err


def test_execute_run_strips_separator(
    parser: ArgumentParser,
    monkeypatch: pytest.MonkeyPatch,
):
    received_args: list[list[str]] = []
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix",
        lambda prefix, binary, args, **kw: (received_args.append(args), 0)[1],
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.get_or_create",
        lambda self, key, specs, channels: __import__("pathlib").Path("/fake"),
    )
    monkeypatch.setattr(
        "conda_exec.binaries.find_binary",
        lambda prefix, name: __import__("pathlib").Path("/fake/bin/ruff"),
    )
    args = parser.parse_args(["ruff", "--", "--check", "."])
    rc = execute_run(args)
    assert rc == 0
    assert received_args[0] == ["--check", "."]


def test_execute_run_refresh_removes_cache(
    parser: ArgumentParser,
    monkeypatch: pytest.MonkeyPatch,
):
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.get_or_create",
        lambda self, key, specs, channels: __import__("pathlib").Path("/fake"),
    )
    monkeypatch.setattr(
        "conda_exec.binaries.find_binary",
        lambda prefix, name: __import__("pathlib").Path("/fake/bin/ruff"),
    )
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix", lambda prefix, binary, args, **kw: 0
    )
    args = parser.parse_args(["--refresh", "ruff"])
    rc = execute_run(args)
    assert rc == 0
    assert len(removed) == 1


def test_execute_run_binary_not_found(
    parser: ArgumentParser,
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.get_or_create",
        lambda self, key, specs, channels: __import__("pathlib").Path("/fake"),
    )
    monkeypatch.setattr("conda_exec.binaries.find_binary", lambda prefix, name: None)
    args = parser.parse_args(["ruff"])
    rc = execute_run(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err
    assert "hint:" in err


def test_execute_run_passes_activate(
    parser: ArgumentParser,
    monkeypatch: pytest.MonkeyPatch,
):
    received_kwargs: list[dict] = []
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix",
        lambda prefix, binary, args, **kw: (received_kwargs.append(kw), 0)[1],
    )
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.get_or_create",
        lambda self, key, specs, channels: __import__("pathlib").Path("/fake"),
    )
    monkeypatch.setattr(
        "conda_exec.binaries.find_binary",
        lambda prefix, name: __import__("pathlib").Path("/fake/bin/ruff"),
    )
    args = parser.parse_args(["--activate", "ruff"])
    rc = execute_run(args)
    assert rc == 0
    assert received_kwargs[0]["activate"] is True


def test_execute_run_progress_on_cache_miss(
    parser: ArgumentParser,
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("conda_exec.cache.CacheManager.exists", lambda self, key: False)
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.get_or_create",
        lambda self, key, specs, channels: __import__("pathlib").Path("/fake"),
    )
    monkeypatch.setattr(
        "conda_exec.binaries.find_binary",
        lambda prefix, name: __import__("pathlib").Path("/fake/bin/ruff"),
    )
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix", lambda prefix, binary, args, **kw: 0
    )
    args = parser.parse_args(["ruff"])
    rc = execute_run(args)
    assert rc == 0
    err = capsys.readouterr().err
    assert "Creating environment for ruff..." in err
    assert "done" in err


def test_execute_run_no_progress_on_cache_hit(
    parser: ArgumentParser,
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("conda_exec.cache.CacheManager.exists", lambda self, key: True)
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.get_or_create",
        lambda self, key, specs, channels: __import__("pathlib").Path("/fake"),
    )
    monkeypatch.setattr(
        "conda_exec.binaries.find_binary",
        lambda prefix, name: __import__("pathlib").Path("/fake/bin/ruff"),
    )
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix", lambda prefix, binary, args, **kw: 0
    )
    args = parser.parse_args(["ruff"])
    rc = execute_run(args)
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_execute_run_conda_exec_error(
    parser: ArgumentParser,
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    from conda_exec.exceptions import SolveError

    def fail_solve(self, key, specs, channels):
        raise SolveError("ruff", "no candidates")

    monkeypatch.setattr("conda_exec.cache.CacheManager.get_or_create", fail_solve)
    args = parser.parse_args(["ruff"])
    rc = execute_run(args)
    assert rc == 1
    assert "no candidates" in capsys.readouterr().err
