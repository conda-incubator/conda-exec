"""Tests for conda_exec.run."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_subprocess import FakeProcess

from conda.common.path import BIN_DIRECTORY

from conda_exec.run import build_activated_env, run_in_prefix


@pytest.fixture
def patch_bin_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda_exec.run.BIN_DIRECTORY", "bin")


@pytest.mark.usefixtures("patch_bin_dir")
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
    assert str(prefix / BIN_DIRECTORY) in env["PATH"].split(os.pathsep)


@pytest.mark.usefixtures("patch_bin_dir")
def test_run_in_prefix_forwards_exit_code(
    prefix: Path,
    binary: Path,
    fp: FakeProcess,
):
    fp.register([str(binary)], returncode=42)
    rc = run_in_prefix(prefix, binary, [])
    assert rc == 42


def raise_on_run(exc: Exception):
    """Return a callable that raises the given exception."""

    def raiser(*args, **kwargs):
        raise exc

    return raiser


@pytest.mark.usefixtures("patch_bin_dir")
@pytest.mark.parametrize(
    ("exception", "exit_code", "expected_message"),
    [
        pytest.param(
            FileNotFoundError("mytool"),
            127,
            "command not found",
            id="file-not-found",
        ),
        pytest.param(
            PermissionError("mytool"),
            126,
            "permission denied",
            id="permission-denied",
        ),
    ],
)
def test_run_in_prefix_subprocess_error(
    prefix: Path,
    binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    exception: Exception,
    exit_code: int,
    expected_message: str,
):
    monkeypatch.setattr(subprocess, "run", raise_on_run(exception))
    rc = run_in_prefix(prefix, binary, [])
    assert rc == exit_code
    assert expected_message in capsys.readouterr().err


@pytest.mark.usefixtures("patch_bin_dir")
def test_run_in_prefix_with_activate(
    prefix: Path,
    binary: Path,
    fp: FakeProcess,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "conda_exec.run.build_activated_env",
        lambda env_prefix: {
            "PATH": str(prefix / BIN_DIRECTORY),
            "CONDA_PREFIX": str(prefix),
        },
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
        def build_activate(self, prefix_str):
            return fake_activation

    monkeypatch.setattr("conda.common.compat.on_win", False)
    monkeypatch.setattr("conda.activate.PosixActivator", FakeActivator)
    monkeypatch.setenv("CONDA_OLD_VAR", "should-be-removed")

    env = build_activated_env(prefix)
    assert env["CONDA_PREFIX"] == str(prefix)
    assert env["MY_VAR"] == "hello"
    assert "CONDA_OLD_VAR" not in env
