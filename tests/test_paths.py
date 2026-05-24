"""Tests for conda_exec.paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from conda_exec.paths import data_dir, envs_dir


@pytest.fixture(autouse=True)
def clear_cache():
    data_dir.cache_clear()
    yield
    data_dir.cache_clear()


def test_data_dir_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    target = tmp_path / "custom-exec"
    monkeypatch.setenv("CONDA_EXEC_HOME", str(target))
    assert data_dir() == target


def test_data_dir_default_unix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONDA_EXEC_HOME", raising=False)
    monkeypatch.setattr("conda.common.compat.on_win", False)
    result = data_dir()
    assert result == Path.home() / ".conda" / "exec"


def test_data_dir_default_windows_primary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """On Windows, if ~/.conda/exec exists, use it as primary."""
    primary = tmp_path / ".conda" / "exec"
    primary.mkdir(parents=True)
    monkeypatch.delenv("CONDA_EXEC_HOME", raising=False)
    monkeypatch.setattr("conda.common.compat.on_win", True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    result = data_dir()
    assert result == primary


def test_data_dir_default_windows_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """On Windows, if ~/.conda/exec does not exist, fall back to platformdirs."""
    fallback = str(tmp_path / "AppData" / "Local" / "conda" / "conda")
    monkeypatch.delenv("CONDA_EXEC_HOME", raising=False)
    monkeypatch.setattr("conda.common.compat.on_win", True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("platformdirs.user_data_dir", lambda *a, **kw: fallback)
    result = data_dir()
    assert result == Path(fallback) / "exec"


def test_envs_dir_is_subdir_of_data_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("CONDA_EXEC_HOME", str(tmp_path))
    assert envs_dir() == tmp_path / "envs"


def test_data_dir_tilde_expansion(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONDA_EXEC_HOME", "~/conda-exec-test")
    result = data_dir()
    assert "~" not in str(result)
