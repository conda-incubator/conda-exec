"""Optional conda-pypi integration for installing PyPI packages."""

from __future__ import annotations

PYPI_CHANNEL = "conda-pypi"


def is_available() -> bool:
    """Check whether conda-pypi is installed."""
    try:
        import conda_pypi  # noqa: F401

        return True
    except ImportError:
        return False
