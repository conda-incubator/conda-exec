"""Performance benchmarks for conda-exec.

Focuses on operations that exercise conda's APIs and could regress
as conda or conda-exec evolve. Trivial pure-Python helpers are
excluded since they'll never be the bottleneck.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

pytestmark = pytest.mark.benchmark


def test_bench_plugin_import(benchmark: BenchmarkFixture) -> None:
    """Full plugin module import chain through conda.plugins."""
    import importlib

    import conda_exec.plugin

    def reimport():
        importlib.reload(conda_exec.plugin)

    benchmark(reimport)


def test_bench_matchspec_parsing(benchmark: BenchmarkFixture) -> None:
    """MatchSpec parsing, the core cost of cache_key computation."""
    from conda.models.match_spec import MatchSpec

    specs = [
        "ruff>=0.4,<1.0",
        "python>=3.12",
        "numpy>=1.26",
        "pandas>=2.0,<3.0",
        "scipy>=1.11",
    ]

    def parse_all():
        return [str(MatchSpec(s)) for s in specs]

    benchmark(parse_all)


def test_bench_cache_key_simple(benchmark: BenchmarkFixture) -> None:
    """Cache key for a single-spec invocation (most common case)."""
    from conda_exec.cache import CacheManager

    cm = CacheManager(envs_dir=Path("/tmp/fake"))
    benchmark(cm.cache_key, "ruff", ["ruff"], ["conda-forge"])


def test_bench_cache_key_complex(benchmark: BenchmarkFixture) -> None:
    """Cache key with multiple specs and channels (worst case)."""
    from conda_exec.cache import CacheManager

    cm = CacheManager(envs_dir=Path("/tmp/fake"))
    specs = [
        "ruff>=0.4,<1.0",
        "python>=3.12",
        "numpy>=1.26",
        "pandas>=2.0,<3.0",
        "scipy>=1.11",
    ]
    channels = ["conda-forge", "bioconda", "defaults"]

    benchmark(cm.cache_key, "ruff", specs, channels)


def test_bench_prefix_data_load(benchmark: BenchmarkFixture) -> None:
    """Loading PrefixData for a real conda environment."""
    from conda.core.prefix_data import PrefixData

    prefix = sys.prefix

    def load():
        PrefixData._cache_.clear()
        pd = PrefixData(prefix)
        pd.load()

    benchmark(load)


def test_bench_prefix_data_iter_records(benchmark: BenchmarkFixture) -> None:
    """Iterating all package records in a real prefix."""
    from conda.core.prefix_data import PrefixData

    PrefixData._cache_.clear()
    pd = PrefixData(sys.prefix)

    def iterate():
        return list(pd.iter_records())

    benchmark(iterate)


def test_bench_prefix_data_size(benchmark: BenchmarkFixture) -> None:
    """Computing total environment size from PrefixData."""
    from conda.core.prefix_data import PrefixData

    PrefixData._cache_.clear()
    pd = PrefixData(sys.prefix)
    pd.load()

    benchmark(pd.size)


def test_bench_prefix_data_is_environment(benchmark: BenchmarkFixture) -> None:
    """Checking if a path is a valid conda environment."""
    from conda.core.prefix_data import PrefixData

    pd = PrefixData(sys.prefix)

    benchmark(pd.is_environment)


def test_bench_script_metadata_parse(
    benchmark: BenchmarkFixture, tmp_path: Path
) -> None:
    """Parsing PEP 723 inline metadata from a script file."""
    from conda_exec.script import parse_script_metadata

    script = tmp_path / "bench_script.py"
    script.write_text(
        "# /// script\n"
        '# requires-python = ">=3.12"\n'
        "# dependencies = [\n"
        '#   "requests>=2.31",\n'
        '#   "rich",\n'
        '#   "click>=8.0",\n'
        "# ]\n"
        "#\n"
        "# [tool.conda]\n"
        '# channels = ["conda-forge", "bioconda"]\n'
        "# dependencies = [\n"
        '#   "samtools>=1.19",\n'
        '#   "python=3.12",\n'
        '#   "numpy>=1.26",\n'
        "# ]\n"
        "# ///\n"
        'print("hello")\n'
    )

    benchmark(parse_script_metadata, str(script))


def test_bench_script_metadata_no_block(
    benchmark: BenchmarkFixture, tmp_path: Path
) -> None:
    """Scanning a script with no metadata block (early exit path)."""
    from conda_exec.script import parse_script_metadata

    script = tmp_path / "plain_script.py"
    lines = ["import sys\n"] * 200 + ["print('hello')\n"]
    script.write_text("".join(lines))

    benchmark(parse_script_metadata, str(script))


def test_bench_script_cache_key(benchmark: BenchmarkFixture) -> None:
    """Cache key derivation from script metadata."""
    from conda_exec.cache import CacheManager
    from conda_exec.script import ScriptMetadata

    cm = CacheManager(envs_dir=Path("/tmp/fake"))
    metadata = ScriptMetadata(
        requires_python=">=3.12",
        pypi_dependencies=("requests>=2.31", "rich", "click>=8.0"),
        conda_dependencies=("samtools>=1.19", "python=3.12", "numpy>=1.26"),
        conda_channels=("conda-forge", "bioconda"),
    )

    benchmark(cm.script_cache_key, metadata)
