"""Tests for conda_exec.cli.main."""

from __future__ import annotations

from argparse import ArgumentParser

import pytest

from conda_exec.cli.main import configure_parser


@pytest.fixture()
def parser() -> ArgumentParser:
    p = ArgumentParser()
    configure_parser(p)
    return p


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
    args = parser.parse_args([
        "-c", "bioconda",
        "--spec", "ruff>=0.4",
        "--with", "pytest",
        "--refresh",
        "ruff",
        "check", ".",
    ])
    assert args.channels == ["bioconda"]
    assert args.spec == "ruff>=0.4"
    assert args.with_specs == ["pytest"]
    assert args.refresh is True
    assert args.tool == "ruff"
    assert args.tool_args == ["check", "."]
