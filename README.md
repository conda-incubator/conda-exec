# conda-exec

[![Tests](https://github.com/jezdez/conda-exec/actions/workflows/tests.yml/badge.svg)](https://github.com/jezdez/conda-exec/actions/workflows/tests.yml)
[![Documentation](https://github.com/jezdez/conda-exec/actions/workflows/docs.yml/badge.svg)](https://jezdez.github.io/conda-exec/)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](https://github.com/jezdez/conda-exec/blob/main/LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)

Ephemeral package execution for conda. Run any conda package without installing it permanently.

```bash
conda exec ruff check .
ce ruff check .
```

conda-exec creates a cached, isolated environment for the tool, runs it, and exits. The environment is cached for fast re-use but is not on PATH and is fully disposable. Think `npx` for Node or `uvx` for Python, but for conda packages.

## Installation

```bash
conda install conda-exec
```

Requires `conda-rattler-solver` for fast environment creation.

## Usage

```bash
# Run a tool (creates cached environment on first use)
conda exec ruff check .
ce ruff check .               # standalone alias

# Pin a version
conda exec "ruff>=0.4,<0.5" check .

# Add extra packages
conda exec --with pytest ruff check .
conda exec --with "python=3.12" jupyter lab

# Use a specific channel
conda exec -c bioconda samtools view file.bam

# Run a script with inline dependencies (PEP 723)
conda exec script.py

# Force re-creation of cached environment
conda exec --refresh ruff check .
```

## How it works

1. Computes a cache key from the tool name, specs, and channels
2. Checks `~/.conda/exec/envs/` for a cached environment
3. On cache miss: solves and installs via conda-rattler-solver
4. Finds the binary in the environment's `bin/` directory
5. Runs it directly via `subprocess.run` with PATH prepended
6. Forwards the tool's exit code

## Documentation

Full documentation at [jezdez.github.io/conda-exec](https://jezdez.github.io/conda-exec/).

## Contributing

```bash
pixi install
pixi run check          # lint + format + typecheck
pixi run -e test test   # run tests
```

## License

BSD-3-Clause
