"""Tests for conda_exec.plugin."""

from __future__ import annotations

from conda_exec.plugin import conda_settings, conda_subcommands


def test_registers_exec_subcommand():
    subcommands = list(conda_subcommands())
    names = [sc.name for sc in subcommands]
    assert names == ["exec"]


def test_subcommand_has_summary():
    (sc,) = conda_subcommands()
    assert sc.summary
    assert len(sc.summary) > 10


def test_subcommand_has_action():
    (sc,) = conda_subcommands()
    assert callable(sc.action)


def test_subcommand_has_configure_parser():
    (sc,) = conda_subcommands()
    assert callable(sc.configure_parser)


def test_registers_auto_clean_settings():
    settings = {setting.name: setting for setting in conda_settings()}

    assert sorted(settings) == [
        "conda_exec_auto_clean",
        "conda_exec_clean_age",
        "conda_exec_clean_interval",
    ]
    assert settings["conda_exec_auto_clean"].parameter.default.typify("test") is True
    assert settings["conda_exec_clean_interval"].parameter.default.typify("test") == 50
    assert settings["conda_exec_clean_age"].parameter.default.typify("test") == 30
