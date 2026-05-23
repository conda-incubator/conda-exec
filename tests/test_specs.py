"""Tests for conda_exec.specs."""

from __future__ import annotations

import pytest

from conda_exec.specs import build_specs, cache_key


class _FakeMatchSpec:
    """Minimal stand-in for conda.models.match_spec.MatchSpec."""

    def __init__(self, spec: str) -> None:
        self._spec = spec

    def __str__(self) -> str:
        return self._spec


@pytest.fixture(autouse=True)
def _patch_matchspec(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("conda_exec.specs.MatchSpec", _FakeMatchSpec, raising=False)
    import conda_exec.specs

    monkeypatch.setattr(conda_exec.specs, "MatchSpec", _FakeMatchSpec, raising=False)


def test_cache_key_deterministic():
    key1 = cache_key("ruff", ["ruff"], ["conda-forge"])
    key2 = cache_key("ruff", ["ruff"], ["conda-forge"])
    assert key1 == key2


def test_cache_key_starts_with_tool():
    key = cache_key("ruff", ["ruff"], ["conda-forge"])
    assert key.startswith("ruff--")


def test_cache_key_has_hash():
    key = cache_key("ruff", ["ruff"], ["conda-forge"])
    _, h = key.split("--", 1)
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_cache_key_differs_with_different_specs():
    key1 = cache_key("ruff", ["ruff"], ["conda-forge"])
    key2 = cache_key("ruff", ["ruff>=0.4"], ["conda-forge"])
    assert key1 != key2


def test_cache_key_differs_with_different_channels():
    key1 = cache_key("ruff", ["ruff"], ["conda-forge"])
    key2 = cache_key("ruff", ["ruff"], ["defaults"])
    assert key1 != key2


def test_cache_key_order_independent():
    key1 = cache_key("ruff", ["ruff", "pytest"], ["conda-forge"])
    key2 = cache_key("ruff", ["pytest", "ruff"], ["conda-forge"])
    assert key1 == key2


def test_build_specs_bare_tool():
    assert build_specs("ruff") == ["ruff"]


def test_build_specs_with_spec_override():
    assert build_specs("ruff", spec="ruff>=0.4") == ["ruff>=0.4"]


def test_build_specs_with_extras():
    result = build_specs("ruff", with_specs=["pytest", "python=3.12"])
    assert result == ["ruff", "pytest", "python=3.12"]


def test_build_specs_spec_plus_with():
    result = build_specs("ruff", spec="ruff>=0.4", with_specs=["pytest"])
    assert result == ["ruff>=0.4", "pytest"]
