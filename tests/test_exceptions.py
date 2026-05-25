"""Tests for conda_exec.exceptions."""

from __future__ import annotations

from conda_exec.exceptions import (
    BinaryNotFoundError,
    CondaExecError,
    InvalidToolMatchSpecError,
    SolveError,
    SolverNotAvailableError,
)


def test_solve_error():
    exc = SolveError("ruff", "no solution found")
    assert "ruff" in exc.error_message
    assert "no solution found" in exc.error_message
    assert exc.hints == []
    assert isinstance(exc, CondaExecError)


def test_binary_not_found_error():
    exc = BinaryNotFoundError("ruff")
    assert "ruff" in exc.error_message
    assert "cached environment" in exc.error_message
    assert len(exc.hints) == 2
    assert isinstance(exc, CondaExecError)


def test_invalid_tool_match_spec_error():
    exc = InvalidToolMatchSpecError(
        "../ruff",
        "package name contains invalid characters",
    )
    assert "../ruff" in exc.error_message
    assert "invalid characters" in exc.error_message
    assert exc.hints == []
    assert isinstance(exc, CondaExecError)


def test_solver_not_available_error():
    exc = SolverNotAvailableError()
    assert "conda-rattler-solver" in exc.error_message
    assert len(exc.hints) == 2
    assert isinstance(exc, CondaExecError)
