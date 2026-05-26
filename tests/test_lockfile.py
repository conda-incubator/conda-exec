"""Tests for script lockfile handling."""

from __future__ import annotations

import stat
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from conda.plugins.types import EnvironmentFormat

from conda_exec import lockfile
from conda_exec.exceptions import ScriptLockError

if TYPE_CHECKING:
    from pathlib import Path


def test_sidecar_lock_paths(tmp_path: Path):
    manager = lockfile.ScriptLockManager()
    script = tmp_path / "analysis.py"
    expected = []
    for filename in manager.lock_format.default_filenames:
        expected.extend(
            [
                tmp_path / f"analysis.py.{filename}",
                tmp_path / f"analysis.{filename}",
            ]
        )

    assert manager.sidecar_paths(script) == expected


def test_discover_prefers_embedded_lock(tmp_path: Path):
    manager = lockfile.ScriptLockManager()
    script = tmp_path / "analysis.py"
    script.write_text(
        "# /// conda-exec-lock\n# embedded: true\n# ///\nprint('hello')\n"
    )
    manager.default_sidecar_path(script).write_text("sidecar: true\n")

    script_lock = manager.discover(script)

    assert script_lock is not None
    assert script_lock.source == "embedded"
    assert script_lock.content == "embedded: true"


def test_discover_sidecar_lock(tmp_path: Path):
    manager = lockfile.ScriptLockManager()
    script = tmp_path / "analysis.py"
    script.write_text("print('hello')\n")
    manager.default_sidecar_path(script).write_text("sidecar: true\n")

    script_lock = manager.discover(script)

    assert script_lock is not None
    assert script_lock.source == "sidecar"
    assert script_lock.content == "sidecar: true\n"


def test_write_sidecar_lock(tmp_path: Path):
    manager = lockfile.ScriptLockManager()
    script = tmp_path / "analysis.py"
    path = manager.write_sidecar(script, "lock: true\n")

    assert path == manager.default_sidecar_path(script)
    assert path.read_text() == "lock: true\n"


def test_write_embedded_lock_inserts_after_script_metadata(tmp_path: Path):
    manager = lockfile.ScriptLockManager()
    script = tmp_path / "analysis.py"
    script.write_text(
        "#!/usr/bin/env ce\n"
        "# /// script\n"
        "# [tool.conda]\n"
        "# dependencies = ['numpy']\n"
        "# ///\n"
        "print('hello')\n"
    )
    mode = script.stat().st_mode | stat.S_IXUSR
    script.chmod(mode)

    manager.write_embedded(script, "lock: true\nplatforms:\n  - osx-arm64\n")

    content = script.read_text()
    assert "# /// script\n" in content
    assert "# /// conda-exec-lock\n" in content
    assert "# lock: true\n" in content
    assert "#   - osx-arm64\n" in content
    assert script.stat().st_mode & stat.S_IXUSR


def test_write_embedded_lock_replaces_existing_block(tmp_path: Path):
    manager = lockfile.ScriptLockManager()
    script = tmp_path / "analysis.py"
    script.write_text("# /// conda-exec-lock\n# old: true\n# ///\nprint('hello')\n")

    manager.write_embedded(script, "new: true\n")

    content = script.read_text()
    assert "old: true" not in content
    assert "# new: true\n" in content


def test_export_lock_content_uses_conda_exporter_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    platforms: list[str] = []

    class Environment:
        @classmethod
        def from_prefix(cls, **kwargs):
            return cls()

        def extrapolate(self, platform):
            platforms.append(platform)
            return f"env:{platform}"

    exporter = SimpleNamespace(
        name="conda-lock-v1",
        aliases=("conda-lock",),
        default_filenames=("conda-lock.yml",),
        multiplatform_export=lambda envs: "\n".join(envs),
        export=None,
        environment_format=EnvironmentFormat.lockfile,
    )
    specifier = SimpleNamespace(
        name="conda-lock-v1",
        aliases=("conda-lock",),
        default_filenames=("conda-lock.yml",),
        environment_format=EnvironmentFormat.lockfile,
    )

    monkeypatch.setattr("conda_exec.lockfile.Environment", Environment)
    monkeypatch.setattr(
        lockfile.context.plugin_manager,
        "get_environment_exporter_by_format",
        lambda name: exporter,
    )
    monkeypatch.setattr(
        lockfile.context.plugin_manager,
        "get_environment_specifiers",
        lambda: {"conda-lock-v1": specifier},
    )

    content = lockfile.ScriptLockManager().export_content(
        tmp_path / "prefix",
        ["linux-64", "osx-arm64"],
    )

    assert content == "env:linux-64\nenv:osx-arm64\n"
    assert platforms == ["linux-64", "osx-arm64"]


def test_create_locked_environment_builds_conda_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: (calls.append(args), Result())[1],
    )

    manager = lockfile.ScriptLockManager()
    prefix = manager.create_environment(
        tmp_path,
        tmp_path / "script--abc",
        "lock: true\n",
    )

    assert prefix == tmp_path / "script--abc"
    assert prefix.is_dir()
    assert calls
    command = calls[0]
    assert "create" in command
    assert "--environment-specifier" in command
    assert manager.lock_format.name in command


def test_create_locked_environment_failure_raises_script_lock_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    class Result:
        returncode = 1
        stdout = ""
        stderr = "no lock support"

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Result())

    with pytest.raises(ScriptLockError, match="no lock support"):
        lockfile.ScriptLockManager().create_environment(
            tmp_path,
            tmp_path / "script--abc",
            "lock: true\n",
        )
