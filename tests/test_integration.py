"""Integration tests for conda-exec.

These tests run end-to-end through the real solver and require network
access. They are skipped by default and enabled with ``--run-slow``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture

pytestmark = pytest.mark.slow


@pytest.mark.usefixtures("exec_home")
def test_exec_end_to_end(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("exec", "zlib", "--", "--help")
    assert code in (0, 1, 2)


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
