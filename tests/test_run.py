"""Tests for conda_exec.run."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from conda_exec.run import run_in_prefix


@pytest.fixture()
def _patch_bin_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda_exec.run.BIN_DIRECTORY", "bin")


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_prepends_path(
    fake_prefix: Path,
    fake_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    recorded_envs: list[dict] = []
    recorded_cmds: list[list[str]] = []

    class FakeResult:
        returncode = 0

    def fake_run(cmd, **kwargs):
        recorded_cmds.append(cmd)
        recorded_envs.append(kwargs.get("env", {}))
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    rc = run_in_prefix(fake_prefix, fake_binary, ["--check", "."])
    assert rc == 0
    assert len(recorded_cmds) == 1
    assert recorded_cmds[0] == [str(fake_binary), "--check", "."]

    path = recorded_envs[0]["PATH"]
    assert str(fake_prefix / "bin") in path.split(os.pathsep)


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_forwards_exit_code(
    fake_prefix: Path,
    fake_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeResult:
        returncode = 42

    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: FakeResult())
    rc = run_in_prefix(fake_prefix, fake_binary, [])
    assert rc == 42


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_file_not_found(
    fake_prefix: Path,
    fake_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    def raise_fnf(cmd, **kw):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "run", raise_fnf)
    rc = run_in_prefix(fake_prefix, fake_binary, [])
    assert rc == 127
    assert "command not found" in capsys.readouterr().err


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_permission_denied(
    fake_prefix: Path,
    fake_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    def raise_perm(cmd, **kw):
        raise PermissionError(cmd[0])

    monkeypatch.setattr(subprocess, "run", raise_perm)
    rc = run_in_prefix(fake_prefix, fake_binary, [])
    assert rc == 126
    assert "permission denied" in capsys.readouterr().err
