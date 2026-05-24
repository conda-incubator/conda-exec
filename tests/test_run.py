"""Tests for conda_exec.run."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_subprocess import FakeProcess

from conda_exec.run import run_in_prefix


@pytest.fixture()
def _patch_bin_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda_exec.run.BIN_DIRECTORY", "bin")


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_prepends_path(
    prefix: Path,
    binary: Path,
    fp: FakeProcess,
):
    recorder = fp.register([str(binary), "--check", "."], returncode=0)

    rc = run_in_prefix(prefix, binary, ["--check", "."])
    assert rc == 0
    assert recorder.call_count() == 1

    env = recorder.first_call.kwargs["env"]
    assert str(prefix / "bin") in env["PATH"].split(os.pathsep)


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_forwards_exit_code(
    prefix: Path,
    binary: Path,
    fp: FakeProcess,
):
    fp.register([str(binary)], returncode=42)
    rc = run_in_prefix(prefix, binary, [])
    assert rc == 42


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_file_not_found(
    prefix: Path,
    binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    monkeypatch.setattr(subprocess, "run", _raise(FileNotFoundError(str(binary))))
    rc = run_in_prefix(prefix, binary, [])
    assert rc == 127
    assert "command not found" in capsys.readouterr().err


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_permission_denied(
    prefix: Path,
    binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    monkeypatch.setattr(subprocess, "run", _raise(PermissionError(str(binary))))
    rc = run_in_prefix(prefix, binary, [])
    assert rc == 126
    assert "permission denied" in capsys.readouterr().err


def _raise(exc: Exception):
    def _inner(*args, **kwargs):
        raise exc

    return _inner
