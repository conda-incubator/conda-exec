# Dependency resolution model

conda-exec has two execution modes. When an environment is needed, each
mode turns user input into one conda solve or one lockfile-based environment
creation.

- Tool mode starts from a package spec in the `TOOL` position.
- Script mode starts from PEP 723 metadata in a Python file.

Both modes create ordinary conda prefixes under the cache directory. A
script without metadata or CLI dependency options is the exception: it runs
directly with the current Python interpreter.

## Tool mode

For a command like:

```bash
conda exec --with pytest -c conda-forge "ruff>=0.4,<0.5" check .
```

conda-exec builds:

- tool name: `ruff`
- specs: `["ruff>=0.4,<0.5", "pytest"]`
- channels: `["conda-forge"]`
- command arguments: `["check", "."]`

The specs are parsed as conda match specs. The tool name is extracted from
the first spec and is later used for binary discovery.

After solving and installing the environment, conda-exec looks for an
executable named `ruff` in the prefix's platform-correct binary directory.

## Script mode

For a script with:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
#
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["numpy>=2"]
# ///
```

conda-exec builds:

- conda specs from `[tool.conda].dependencies`
- PyPI specs from top-level `dependencies`
- channels from `[tool.conda].channels`
- a Python spec from `requires-python`

If no spec starts with `python`, conda-exec adds one automatically. With
`requires-python = ">=3.12"`, the added spec is `python >=3.12`. Without
`requires-python`, the added spec is a bare `python`.

After creating the environment, conda-exec finds that environment's Python
interpreter and runs the script with it.

## PyPI dependencies

Top-level PEP 723 `dependencies` are PyPI requirements. conda-exec supports
them through `conda-pypi`.

When PyPI dependencies are present:

1. conda-exec verifies that `conda-pypi` is importable.
2. The `conda-pypi` channel is appended to the channel list.
3. PyPI requirements are added to the same solve as conda specs.

This means mixed conda and PyPI scripts still create one environment and
one cache entry.

If `conda-pypi` is missing, conda-exec fails before solving so the user gets
a clear setup error instead of a solver error.

## Channel defaults

Tool mode uses `conda-forge` when no `-c/--channel` flags are provided.

Script mode combines channels from metadata and the CLI:

1. channels declared in `[tool.conda].channels`
2. channels passed with `-c/--channel`
3. `conda-forge` if the combined list is empty

When PyPI dependencies are present, `conda-pypi` is appended after those
channels.

## Cache keys and solving

The cache key determines whether conda-exec solves or reuses an existing
prefix.

Tool cache keys are derived from normalized specs and channels. Script
metadata cache keys are derived from dependency metadata. Script lock cache
keys are derived from lock content.

This creates predictable behavior:

- changing command arguments does not create a new environment
- changing package specs creates a new environment
- changing script code alone does not create a new environment
- changing script dependency metadata creates a new environment
- changing generated lock content creates a new environment

`--refresh` removes the cache entry for the current dependency input and
forces a new solve or lock-based environment creation.

## Lock data path

When lock data is discovered and matches the current dependency input,
conda-exec skips solving from metadata. It asks conda to create an
environment from the lockfile format instead.

This path still creates a cached prefix. The difference is that package
versions and builds come from lock content rather than a fresh solver
decision.

Lock data is ignored when command-line flags change the dependency input,
such as `--with` or `--channel`, and when the user explicitly passes
`--ignore-lock` or `--refresh`.

## Failure surfaces

Resolution can fail at several distinct stages:

- match spec parsing fails before solving
- no solver backend is available
- conda cannot solve the requested specs
- `conda-pypi` is required but unavailable
- lock exporter or specifier plugins are unavailable
- the environment solves but the expected binary is not present

conda-exec keeps these stages separate so errors can point to the right
fix: install a missing plugin, adjust channels, change a spec, refresh a
cache, or use a named environment for packages with unusual executables.
