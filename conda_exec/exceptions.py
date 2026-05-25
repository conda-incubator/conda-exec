"""Exceptions for conda-exec."""

from __future__ import annotations

from conda.exceptions import CondaError


class CondaExecError(CondaError):
    """Base exception for conda-exec operations."""

    error_message: str = ""
    hints: list[str] = []


class SolveError(CondaExecError):
    """Raised when dependency resolution fails."""

    def __init__(self, tool: str, detail: str) -> None:
        self.error_message = f"failed to solve environment for '{tool}': {detail}"
        self.hints: list[str] = []
        super().__init__(self.error_message)


class InvalidToolMatchSpecError(CondaExecError):
    """Raised when the tool argument is not a valid conda match spec."""

    def __init__(self, spec: str, detail: str) -> None:
        self.error_message = f"invalid match spec for tool {spec!r}: {detail}"
        self.hints: list[str] = []
        super().__init__(self.error_message)


class BinaryNotFoundError(CondaExecError):
    """Raised when a binary is not found in the cached environment."""

    def __init__(self, binary: str) -> None:
        self.error_message = f"binary '{binary}' not found in cached environment"
        self.hints = [
            f"the package may not provide a '{binary}' executable",
            "check the package contents with 'conda search --info <package>'",
        ]
        super().__init__(self.error_message)


class SolverNotAvailableError(CondaExecError):
    """Raised when conda-rattler-solver is not installed."""

    def __init__(self) -> None:
        self.error_message = "conda-rattler-solver is required but not installed"
        self.hints = [
            "install it with: conda install -n base conda-rattler-solver",
            "or set 'solver: rattler' in your .condarc",
        ]
        super().__init__(self.error_message)


class PyPIDependencyError(CondaExecError):
    """Raised when PyPI dependencies are declared but conda-pypi is unavailable."""

    def __init__(self) -> None:
        self.error_message = (
            "script declares PyPI dependencies but conda-pypi is not installed"
        )
        self.hints = [
            "install it with: conda install -n base conda-pypi",
            "or remove the top-level 'dependencies' from the script metadata",
        ]
        super().__init__(self.error_message)


class ScriptMetadataError(CondaExecError):
    """Raised when inline script metadata is invalid."""

    def __init__(self, detail: str) -> None:
        self.error_message = f"invalid inline script metadata: {detail}"
        self.hints: list[str] = []
        super().__init__(self.error_message)


class PythonVersionError(CondaExecError):
    """Raised when a script's requires-python constraint is not satisfied."""

    def __init__(self, required: str, available: str) -> None:
        self.error_message = (
            f"script requires Python {required}, but the environment has {available}"
        )
        self.hints: list[str] = []
        super().__init__(self.error_message)
