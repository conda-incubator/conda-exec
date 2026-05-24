"""Tests for conda_exec.run."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_subprocess import FakeProcess

from conda_exec.run import build_activated_env, run_in_prefix


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


@pytest.mark.usefixtures("_patch_bin_dir")
def test_run_in_prefix_with_activate(
    prefix: Path,
    binary: Path,
    fp: FakeProcess,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "conda_exec.run.build_activated_env",
        lambda p: {"PATH": str(prefix / "bin"), "CONDA_PREFIX": str(prefix)},
    )
    recorder = fp.register([str(binary)], returncode=0)

    rc = run_in_prefix(prefix, binary, [], activate=True)
    assert rc == 0
    env = recorder.first_call.kwargs["env"]
    assert env["CONDA_PREFIX"] == str(prefix)


def test_build_activated_env(
    prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    fake_activation = {
        "export_vars": {"CONDA_PREFIX": str(prefix), "MY_VAR": "hello"},
        "unset_vars": ["CONDA_OLD_VAR"],
    }

    class FakeActivator:
        def build_activate(self, p):
            return fake_activation

    monkeypatch.setattr("conda.common.compat.on_win", False)
    monkeypatch.setattr("conda.activate.PosixActivator", FakeActivator)
    monkeypatch.setenv("CONDA_OLD_VAR", "should-be-removed")

    env = build_activated_env(prefix)
    assert env["CONDA_PREFIX"] == str(prefix)
    assert env["MY_VAR"] == "hello"
    assert "CONDA_OLD_VAR" not in env


def _raise(exc: Exception):
    def _inner(*args, **kwargs):
        raise exc

    return _inner
