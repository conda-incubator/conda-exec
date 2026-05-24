# Quickstart

## Installation

```bash
conda install conda-exec
```

conda-exec requires `conda-rattler-solver` for fast environment creation.
If you use [conda-express (cx)](https://github.com/conda-incubator/conda-express),
it is already included.

## Basic usage

Run any conda package without installing it:

```bash
conda exec ruff check .
```

Or use the short alias:

```bash
conda x ruff check .
```

The first invocation creates a cached environment. Subsequent runs reuse the cache and start instantly.

## Version constraints

Pin a specific version using a match spec as the tool argument:

```bash
conda exec "ruff>=0.4,<0.5" check .
```

The binary name is extracted from the match spec automatically.

## Extra packages

Add additional packages to the ephemeral environment:

```bash
conda exec --with pytest ruff check .
conda exec --with "python=3.12" jupyter lab
```

## Custom channels

Use packages from other channels:

```bash
conda exec -c bioconda samtools view file.bam
```
