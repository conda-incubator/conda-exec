"""Integration tests for conda-exec.

These tests run end-to-end through the real solver and require network
access. They are skipped by default and enabled with ``--run-slow``.
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture

pytestmark = pytest.mark.slow


@pytest.mark.usefixtures("exec_home")
def test_exec_end_to_end_binary_not_found(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("exec", "zlib")
    assert code == 1
    assert "not found" in err


@pytest.mark.usefixtures("exec_home")
def test_exec_end_to_end_with_binary(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("exec", "jq", "--", "--help")
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_exec_list_empty(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("exec", "--list")
    assert code == 0
    assert "No cached environments." in out


@pytest.mark.usefixtures("exec_home")
def test_exec_clean_empty(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("exec", "--clean", "--yes")
    assert code == 0
    assert "No cached environments" in out


@pytest.mark.usefixtures("exec_home")
def test_script_no_metadata_runs_directly(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script("import sys; print(sys.version_info.major)")
    _, _, code = conda_cli("exec", str(script))
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_script_conda_only_deps(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            print("conda-only ok")
        """)
    )
    _, _, code = conda_cli("exec", str(script))
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_script_pypi_only_deps(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # dependencies = ["six"]
            # ///
            import six
            print(f"six={six.__version__}")
        """)
    )
    _, _, code = conda_cli("exec", str(script))
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_script_mixed_conda_and_pypi_deps(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # dependencies = ["six"]
            #
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            import six
            print(f"mixed ok six={six.__version__}")
        """)
    )
    _, _, code = conda_cli("exec", str(script))
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_script_with_requires_python(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # requires-python = ">=3.10"
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            import sys
            assert sys.version_info >= (3, 10)
        """)
    )
    _, _, code = conda_cli("exec", str(script))
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_script_cache_reuse(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            print("cached")
        """)
    )
    _, err1, code1 = conda_cli("exec", str(script))
    assert code1 == 0
    assert "Creating environment" in err1

    _, err2, code2 = conda_cli("exec", str(script))
    assert code2 == 0
    assert "Creating environment" not in err2


@pytest.mark.usefixtures("exec_home")
def test_script_refresh_recreates_env(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            print("refreshed")
        """)
    )
    conda_cli("exec", str(script))

    _, err, code = conda_cli("exec", "--refresh", str(script))
    assert code == 0
    assert "Creating environment" in err


@pytest.mark.usefixtures("exec_home")
def test_script_with_cli_extra_deps(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            print("cli-extras ok")
        """)
    )
    _, _, code = conda_cli("exec", "--with", "bzip2", str(script))
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_script_passes_args_to_script(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            import sys
            assert len(sys.argv) > 1, "expected arguments"
            assert sys.argv[1] == "hello"
        """)
    )
    _, _, code = conda_cli("exec", str(script), "--", "hello", "world")
    assert code == 0


@pytest.mark.usefixtures("exec_home")
def test_script_appears_in_list(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            print("listed")
        """)
    )
    conda_cli("exec", str(script))

    out, err, code = conda_cli("exec", "--list")
    assert code == 0
    assert "script" in out.lower()


@pytest.mark.usefixtures("exec_home")
def test_script_clean_removes_env(
    conda_cli: CondaCLIFixture,
    write_script: Callable[..., Path],
    exec_home: Path,
):
    script = write_script(
        textwrap.dedent("""\
            # /// script
            # [tool.conda]
            # dependencies = ["zlib"]
            # channels = ["conda-forge"]
            # ///
            print("to-clean")
        """)
    )
    conda_cli("exec", str(script))

    envs_dir = exec_home / "envs"
    assert any(envs_dir.iterdir())

    conda_cli("exec", "--clean", "--all", "--yes")

    remaining = list(envs_dir.iterdir()) if envs_dir.exists() else []
    assert len(remaining) == 0
