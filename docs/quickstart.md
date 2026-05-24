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

Or use the standalone `ce` command:

```bash
ce ruff check .
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

## Run scripts

Run a Python script that declares its dependencies inline using
[PEP 723](https://peps.python.org/pep-0723/) metadata:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "rich"]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19"]
# ///

import requests
from rich import print
print("Hello from conda exec!")
```

```bash
conda exec script.py
```

conda-exec parses the inline metadata, creates a cached environment with all
declared dependencies (both conda and PyPI), and runs the script.

Scripts without metadata run directly with the current Python.
