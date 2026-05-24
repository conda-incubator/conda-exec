# conda-exec

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

## License

BSD-3-Clause
