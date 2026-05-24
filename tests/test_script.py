"""Tests for PEP 723 inline script metadata parsing and execution."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from conda_exec.execute import execute_run
from conda_exec.script import (
    ScriptMetadata,
    extract_script_block,
    parse_script_metadata,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from collections.abc import Callable
    from pathlib import Path


SCRIPT_CONDA_ONLY = textwrap.dedent("""\
    # /// script
    # [tool.conda]
    # dependencies = ["samtools>=1.19"]
    # channels = ["conda-forge", "bioconda"]
    # ///
    print("hello")
""")

SCRIPT_PYPI_ONLY = textwrap.dedent("""\
    # /// script
    # requires-python = ">=3.12"
    # dependencies = ["requests>=2.31", "rich"]
    # ///
    import requests
""")

SCRIPT_BOTH = textwrap.dedent("""\
    # /// script
    # requires-python = ">=3.12"
    # dependencies = ["requests"]
    #
    # [tool.conda]
    # channels = ["conda-forge", "bioconda"]
    # dependencies = ["samtools>=1.19"]
    # ///
    print("hello")
""")

SCRIPT_NO_METADATA = "print('hello world')\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # dependencies = ["requests"]
                # ///
            """),
            'dependencies = ["requests"]',
            id="simple",
        ),
        pytest.param(
            textwrap.dedent("""\
                #!/usr/bin/env python3
                # /// script
                # requires-python = ">=3.12"
                # dependencies = [
                #   "requests<3",
                #   "rich",
                # ]
                # ///
                import requests
            """),
            'requires-python = ">=3.12"\n'
            "dependencies = [\n"
            '  "requests<3",\n'
            '  "rich",\n'
            "]",
            id="multiline-with-shebang",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # dependencies = ["requests"]
                #
                # [tool.conda]
                # dependencies = ["samtools>=1.19"]
                # channels = ["conda-forge", "bioconda"]
                # ///
            """),
            'dependencies = ["requests"]\n'
            "\n"
            "[tool.conda]\n"
            'dependencies = ["samtools>=1.19"]\n'
            'channels = ["conda-forge", "bioconda"]',
            id="with-tool-conda",
        ),
        pytest.param(
            "print('hello')\n",
            None,
            id="no-block",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # dependencies = ["requests"]
            """),
            None,
            id="unclosed-block",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// notebook
                # dependencies = ["jupyter"]
                # ///
            """),
            None,
            id="wrong-block-type",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                not a comment line
                # ///
            """),
            None,
            id="invalid-line-inside-block",
        ),
    ],
)
def test_extract_script_block(text: str, expected: str | None):
    assert extract_script_block(text) == expected


def test_extract_script_block_unclosed_warns(capsys: pytest.CaptureFixture):
    text = textwrap.dedent("""\
        # /// script
        # dependencies = ["requests"]
    """)
    assert extract_script_block(text) is None
    assert "unclosed" in capsys.readouterr().err


def test_extract_script_block_from_file_iterator():
    lines = [
        "#!/usr/bin/env python3\n",
        "# /// script\n",
        '# dependencies = ["click"]\n',
        "# ///\n",
        "import click\n",
    ]
    assert extract_script_block(lines) == 'dependencies = ["click"]'


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # [tool.conda]
                # dependencies = ["samtools>=1.19", "python=3.12"]
                # channels = ["conda-forge", "bioconda"]
                # ///
            """),
            ScriptMetadata(
                conda_dependencies=("samtools>=1.19", "python=3.12"),
                conda_channels=("conda-forge", "bioconda"),
            ),
            id="conda-only",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # requires-python = ">=3.11"
                # dependencies = ["requests>=2.31", "rich"]
                # ///
            """),
            ScriptMetadata(
                requires_python=">=3.11",
                pypi_dependencies=("requests>=2.31", "rich"),
            ),
            id="pypi-only",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # requires-python = ">=3.12"
                # dependencies = ["requests>=2.31", "rich"]
                #
                # [tool.conda]
                # channels = ["conda-forge", "bioconda"]
                # dependencies = ["samtools>=1.19"]
                # ///
            """),
            ScriptMetadata(
                requires_python=">=3.12",
                pypi_dependencies=("requests>=2.31", "rich"),
                conda_dependencies=("samtools>=1.19",),
                conda_channels=("conda-forge", "bioconda"),
            ),
            id="both",
        ),
        pytest.param(
            "print('hello')",
            None,
            id="no-block",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # this is not valid toml [[[
                # ///
            """),
            None,
            id="malformed-toml",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # ///
            """),
            ScriptMetadata(),
            id="empty-block",
        ),
        pytest.param(
            textwrap.dedent("""\
                # /// script
                # dependencies = []
                #
                # [tool.conda]
                # dependencies = []
                # channels = []
                # ///
            """),
            ScriptMetadata(),
            id="empty-deps",
        ),
    ],
)
def test_parse_script_metadata(text: str, expected: ScriptMetadata | None):
    assert parse_script_metadata(text) == expected


def test_parse_script_metadata_from_file(tmp_path: Path):
    script = tmp_path / "test_script.py"
    script.write_text(
        textwrap.dedent("""\
        #!/usr/bin/env python3
        # /// script
        # dependencies = ["click"]
        # ///
        import click
    """)
    )
    result = parse_script_metadata(str(script))
    assert result is not None
    assert result.pypi_dependencies == ("click",)


def test_script_detection_routes_to_script_handler(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
):
    script = write_script(SCRIPT_NO_METADATA)
    calls: list[str] = []
    monkeypatch.setattr(
        "conda_exec.execute.execute_script",
        lambda args, path: (calls.append("script"), 0)[1],
    )
    args = parser.parse_args([str(script)])
    execute_run(args)
    assert calls == ["script"]


def test_script_no_metadata_runs_directly(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
):
    script = write_script(SCRIPT_NO_METADATA)
    run_calls: list[list[str]] = []

    def record_run(binary_args, **kwargs):
        import subprocess

        run_calls.append(binary_args)
        return subprocess.CompletedProcess(binary_args, 0)

    monkeypatch.setattr("subprocess.run", record_run)
    args = parser.parse_args([str(script)])
    rc = execute_run(args)
    assert rc == 0
    assert len(run_calls) == 1
    assert str(script.resolve()) in run_calls[0][1]


@pytest.mark.parametrize(
    ("content", "pypi_available", "expected_specs", "expected_channels"),
    [
        pytest.param(
            SCRIPT_CONDA_ONLY,
            False,
            ["samtools>=1.19"],
            ["bioconda"],
            id="conda-only",
        ),
        pytest.param(
            SCRIPT_PYPI_ONLY,
            True,
            ["requests>=2.31", "rich"],
            ["conda-pypi"],
            id="pypi-only",
        ),
        pytest.param(
            SCRIPT_BOTH,
            True,
            ["samtools>=1.19", "requests"],
            ["bioconda", "conda-pypi"],
            id="both",
        ),
    ],
)
def test_script_env_specs_and_channels(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    script_env: list[dict],
    monkeypatch: pytest.MonkeyPatch,
    content: str,
    pypi_available: bool,
    expected_specs: list[str],
    expected_channels: list[str],
):
    script = write_script(content)
    if pypi_available:
        monkeypatch.setattr("conda_exec.pypi.is_available", lambda: True)

    args = parser.parse_args([str(script)])
    rc = execute_run(args)
    assert rc == 0
    assert len(script_env) == 1
    for spec in expected_specs:
        assert spec in script_env[0]["specs"]
    for channel in expected_channels:
        assert channel in script_env[0]["channels"]
    assert any(s.startswith("python") for s in script_env[0]["specs"])


def test_script_pypi_deps_without_conda_pypi_fails(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    script = write_script(SCRIPT_PYPI_ONLY)
    monkeypatch.setattr("conda_exec.pypi.is_available", lambda: False)

    args = parser.parse_args([str(script)])
    rc = execute_run(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "conda-pypi is not installed" in err


def test_script_with_cli_extras(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    script_env: list[dict],
):
    script = write_script(SCRIPT_CONDA_ONLY)
    args = parser.parse_args(["--with", "pytest", "-c", "defaults", str(script)])
    rc = execute_run(args)
    assert rc == 0
    assert len(script_env) == 1
    assert "pytest" in script_env[0]["specs"]
    assert "defaults" in script_env[0]["channels"]


@pytest.mark.parametrize(
    ("extra_argv", "expected_in_args", "not_expected"),
    [
        pytest.param(
            ["--verbose", "output.txt"],
            ["--verbose", "output.txt"],
            [],
            id="passthrough",
        ),
        pytest.param(
            ["--", "--flag"],
            ["--flag"],
            ["--"],
            id="separator-stripped",
        ),
    ],
)
def test_script_tool_args(
    exec_home: Path,
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    solver_calls: list[dict],
    monkeypatch: pytest.MonkeyPatch,
    extra_argv: list[str],
    expected_in_args: list[str],
    not_expected: list[str],
):
    from conda.common.compat import on_win

    script = write_script(SCRIPT_CONDA_ONLY)
    received: list[tuple] = []

    def fake_find_python(prefix: Path) -> Path | None:
        import stat

        python_name = "python.exe" if on_win else "python"
        python_short = python_name if on_win else f"bin/{python_name}"
        python = prefix / python_short
        python.parent.mkdir(parents=True, exist_ok=True)
        if on_win:
            python.write_text("")
        else:
            python.write_text("#!/bin/sh\n")
            python.chmod(python.stat().st_mode | stat.S_IXUSR)
        return python

    monkeypatch.setattr("conda_exec.binaries.find_python", fake_find_python)
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix",
        lambda prefix, binary, args, **kw: (
            received.append((prefix, binary, args)),
            0,
        )[1],
    )

    args = parser.parse_args([str(script), *extra_argv])
    rc = execute_run(args)
    assert rc == 0
    assert len(received) == 1
    run_args = received[0][2]
    assert str(script.resolve()) == run_args[0]
    for val in expected_in_args:
        assert val in run_args
    for val in not_expected:
        assert val not in run_args


def test_script_python_not_found_in_env(
    exec_home: Path,
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    solver_calls: list[dict],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    script = write_script(SCRIPT_CONDA_ONLY)
    monkeypatch.setattr("conda_exec.binaries.find_python", lambda prefix: None)

    args = parser.parse_args([str(script)])
    rc = execute_run(args)
    assert rc == 1
    assert "python not found" in capsys.readouterr().err


def test_script_requires_python_becomes_spec(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    script_env: list[dict],
    monkeypatch: pytest.MonkeyPatch,
):
    script = write_script(SCRIPT_PYPI_ONLY)
    monkeypatch.setattr("conda_exec.pypi.is_available", lambda: True)

    args = parser.parse_args([str(script)])
    execute_run(args)
    assert "python >=3.12" in script_env[0]["specs"]


@pytest.mark.usefixtures("script_env")
def test_script_refresh_removes_cache(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
):
    script = write_script(SCRIPT_CONDA_ONLY)
    removed: list[str] = []
    monkeypatch.setattr(
        "conda_exec.cache.CacheManager.remove",
        lambda self, key: removed.append(key),
    )

    args = parser.parse_args(["--refresh", str(script)])
    rc = execute_run(args)
    assert rc == 0
    assert len(removed) == 1


def test_script_cache_key_deterministic(
    exec_home: Path,
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    script_env: list[dict],
):
    script = write_script(SCRIPT_CONDA_ONLY)

    args = parser.parse_args([str(script)])
    execute_run(args)
    key1 = script_env[0]["key"]

    import shutil

    envs = exec_home / "envs"
    for child in envs.iterdir():
        shutil.rmtree(child)
    script_env.clear()

    execute_run(args)
    key2 = script_env[0]["key"]

    assert key1 == key2
    assert key1.startswith("script--")


def test_parse_script_metadata_skips_large_file(tmp_path: Path):
    from conda_exec.script import MAX_SCRIPT_SIZE

    script = tmp_path / "large.py"
    script.write_text("# /// script\n# dependencies = ['x']\n# ///\n")
    import os

    os.truncate(script, MAX_SCRIPT_SIZE + 1)
    assert parse_script_metadata(str(script)) is None


@pytest.mark.usefixtures("exec_home", "solver_calls")
def test_script_requires_python_mismatch(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    """When the resolved Python violates requires-python, give a clear error."""
    import stat

    from conda.common.compat import on_win

    script = write_script(
        "# /// script\n"
        '# requires-python = ">=3.99"\n'
        "# [tool.conda]\n"
        '# dependencies = ["numpy"]\n'
        "# ///\n"
        "print('hello')\n"
    )

    python_name = "python.exe" if on_win else "python"
    python_short = python_name if on_win else f"bin/{python_name}"

    def fake_find_python(prefix: Path) -> Path | None:
        python = prefix / python_short
        python.parent.mkdir(parents=True, exist_ok=True)
        if on_win:
            python.write_text("")
        else:
            python.write_text("#!/bin/sh\n")
            python.chmod(python.stat().st_mode | stat.S_IXUSR)
        return python

    class FakeRecord:
        version = "3.12.4"

    class FakePrefixData:
        def __init__(self, *_args):
            pass

        def get(self, name, default=None):
            if name == "python":
                return FakeRecord()
            return default

    monkeypatch.setattr("conda_exec.binaries.find_python", fake_find_python)
    monkeypatch.setattr(
        "conda.core.prefix_data.PrefixData",
        FakePrefixData,
    )

    args = parser.parse_args([str(script)])
    rc = execute_run(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "requires Python >=3.99" in err
    assert "3.12.4" in err


def test_script_no_metadata_with_cli_extras(
    parser: ArgumentParser,
    write_script: Callable[..., Path],
    script_env: list[dict],
):
    script = write_script(SCRIPT_NO_METADATA)
    args = parser.parse_args(["--with", "numpy", "-c", "defaults", str(script)])
    rc = execute_run(args)
    assert rc == 0
    assert len(script_env) == 1
    assert "numpy" in script_env[0]["specs"]
    assert "defaults" in script_env[0]["channels"]
