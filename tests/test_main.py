"""Tests for the ``ce`` standalone entry point."""

from __future__ import annotations

from conda_exec.main import main


def test_main_no_args(capsys):
    result = main([])
    assert result == 2
    captured = capsys.readouterr()
    assert "missing TOOL argument" in captured.err


def test_main_list_mode(exec_home, capsys):
    result = main(["--list"])
    assert result == 0


def test_main_dispatches_to_execute(exec_home, solver_calls, monkeypatch):
    from conda.common.compat import on_win
    from conda.common.path import BIN_DIRECTORY

    binary_name = "mytool.exe" if on_win else "mytool"

    def fake_find_binary(prefix, name):
        binary = prefix / BIN_DIRECTORY / binary_name
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text("")
        return binary

    monkeypatch.setattr("conda_exec.binaries.find_binary", fake_find_binary)
    monkeypatch.setattr(
        "conda_exec.run.run_in_prefix", lambda prefix, binary, args, **kw: 0
    )

    result = main(["mytool"])
    assert result == 0
    assert len(solver_calls) == 1
