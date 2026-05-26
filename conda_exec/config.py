"""Configuration helpers for conda-exec."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

DEFAULT_AUTO_CLEAN = True
DEFAULT_CLEAN_INTERVAL = 50
DEFAULT_CLEAN_AGE = 30


@dataclass(frozen=True)
class AutoCleanConfig:
    """Configuration for automatic cache cleanup."""

    enabled: bool
    interval: int
    age_days: int


def validate_positive_int(value: int) -> bool | str:
    """Validate that a conda plugin setting is a positive integer."""
    if value > 0:
        return True
    return "must be greater than zero"


def validate_non_negative_int(value: int) -> bool | str:
    """Validate that a conda plugin setting is zero or greater."""
    if value >= 0:
        return True
    return "must be zero or greater"


def parse_bool_env(value: str) -> bool | None:
    """Parse a boolean environment variable value."""
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def parse_positive_int_env(value: str) -> int | None:
    """Parse a positive integer environment variable value."""
    try:
        parsed = int(value.strip())
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def parse_non_negative_int_env(value: str) -> int | None:
    """Parse a non-negative integer environment variable value."""
    try:
        parsed = int(value.strip())
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def get_conda_plugin_auto_clean_config() -> AutoCleanConfig:
    """Read automatic cleanup settings from conda plugin configuration."""
    from conda.base.context import context

    try:
        plugins = context.plugins
        return AutoCleanConfig(
            enabled=cast(
                "bool",
                getattr(plugins, "conda_exec_auto_clean", DEFAULT_AUTO_CLEAN),
            ),
            interval=cast(
                "int",
                getattr(plugins, "conda_exec_clean_interval", DEFAULT_CLEAN_INTERVAL),
            ),
            age_days=cast(
                "int",
                getattr(plugins, "conda_exec_clean_age", DEFAULT_CLEAN_AGE),
            ),
        )
    except AttributeError:
        return AutoCleanConfig(
            enabled=DEFAULT_AUTO_CLEAN,
            interval=DEFAULT_CLEAN_INTERVAL,
            age_days=DEFAULT_CLEAN_AGE,
        )


def get_auto_clean_config() -> AutoCleanConfig:
    """Read automatic cleanup settings with direct env vars as aliases."""
    config = get_conda_plugin_auto_clean_config()

    enabled = config.enabled
    if "CONDA_EXEC_AUTO_CLEAN" in os.environ:
        parsed = parse_bool_env(os.environ["CONDA_EXEC_AUTO_CLEAN"])
        if parsed is not None:
            enabled = parsed

    interval = config.interval
    if "CONDA_EXEC_CLEAN_INTERVAL" in os.environ:
        parsed = parse_positive_int_env(os.environ["CONDA_EXEC_CLEAN_INTERVAL"])
        if parsed is not None:
            interval = parsed

    age_days = config.age_days
    if "CONDA_EXEC_CLEAN_AGE" in os.environ:
        parsed = parse_non_negative_int_env(os.environ["CONDA_EXEC_CLEAN_AGE"])
        if parsed is not None:
            age_days = parsed

    return AutoCleanConfig(enabled=enabled, interval=interval, age_days=age_days)
