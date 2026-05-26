"""Tests for conda_exec.config."""

from __future__ import annotations

import pytest

from conda_exec.config import (
    AutoCleanConfig,
    get_auto_clean_config,
    parse_bool_env,
    parse_non_negative_int_env,
    parse_positive_int_env,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("NO", False),
        ("off", False),
        ("maybe", None),
    ],
)
def test_parse_bool_env(value: str, expected: bool | None):
    assert parse_bool_env(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", 1),
        ("50", 50),
        ("0", None),
        ("-1", None),
        ("nope", None),
    ],
)
def test_parse_positive_int_env(value: str, expected: int | None):
    assert parse_positive_int_env(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", 0),
        ("30", 30),
        ("-1", None),
        ("nope", None),
    ],
)
def test_parse_non_negative_int_env(value: str, expected: int | None):
    assert parse_non_negative_int_env(value) == expected


def test_direct_env_vars_override_conda_plugin_settings(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "conda_exec.config.get_conda_plugin_auto_clean_config",
        lambda: AutoCleanConfig(enabled=False, interval=10, age_days=20),
    )
    monkeypatch.setenv("CONDA_EXEC_AUTO_CLEAN", "true")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_INTERVAL", "7")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_AGE", "3")

    config = get_auto_clean_config()

    assert config == AutoCleanConfig(enabled=True, interval=7, age_days=3)


def test_invalid_direct_env_vars_fall_back_to_conda_plugin_settings(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "conda_exec.config.get_conda_plugin_auto_clean_config",
        lambda: AutoCleanConfig(enabled=True, interval=10, age_days=20),
    )
    monkeypatch.setenv("CONDA_EXEC_AUTO_CLEAN", "maybe")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_INTERVAL", "0")
    monkeypatch.setenv("CONDA_EXEC_CLEAN_AGE", "-1")

    config = get_auto_clean_config()

    assert config == AutoCleanConfig(enabled=True, interval=10, age_days=20)
