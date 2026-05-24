# Script metadata format

conda-exec supports [PEP 723](https://peps.python.org/pep-0723/) inline
script metadata for declaring dependencies directly inside a Python script.
When you run `conda exec script.py`, conda-exec parses any metadata block
in the file and creates a cached environment with the declared dependencies.

## Block syntax

Metadata is embedded in a comment block delimited by `# /// script` and
`# ///`. Each line inside the block must start with `# ` (hash, space),
and the content is parsed as TOML.

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "rich"]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19"]
# ///
```

The block can appear anywhere in the file. Only the first `# /// script`
block is used. Blank lines within the block use a bare `#` (no trailing
space required).

## Standard fields

These fields follow the PEP 723 specification and are compatible with
other tools that support inline script metadata (such as uv and pipx).

### `requires-python`

Python version constraint as a PEP 440 version specifier.

```python
# /// script
# requires-python = ">=3.11"
# ///
```

Translated to a conda `python` spec in the environment solve. For
example, `requires-python = ">=3.11"` becomes the spec `python >=3.11`.

### `dependencies`

A list of PyPI package names, following PEP 508 syntax.

```python
# /// script
# dependencies = ["requests>=2.28", "rich"]
# ///
```

Requires [conda-pypi](https://github.com/conda-incubator/conda-pypi)
to be installed. When PyPI dependencies are present, the `conda-pypi`
channel is added to the channel list automatically. If conda-pypi is
not installed, conda-exec raises a `PyPIDependencyError`.

## Extension fields

These fields are specific to conda-exec and live under the
`[tool.conda]` TOML table, following PEP 723's convention for
tool-specific configuration.

### `[tool.conda].dependencies`

A list of conda package specs (match specs).

```python
# /// script
# [tool.conda]
# dependencies = ["numpy>=1.24", "pandas", "scipy"]
# ///
```

These are passed directly to the conda solver. Any valid conda match
spec syntax is accepted (e.g. `numpy>=1.24,<2`, `python-dateutil`).

### `[tool.conda].channels`

A list of conda channels to search for packages.

```python
# /// script
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19"]
# ///
```

If no channels are specified (neither in the metadata nor via
`--channel` on the command line), conda-exec defaults to `conda-forge`.

## Automatic Python spec

If no dependency in the combined spec list (conda dependencies, PyPI
dependencies, and `--with` specs) starts with `python`, conda-exec
adds one automatically:

- If `requires-python` is set, the spec is `python <constraint>`
  (e.g. `python >=3.12`).
- Otherwise, a bare `python` spec is added, letting the solver pick
  the best available version.

This ensures that script environments always include a Python
interpreter.

## Field interactions

The metadata fields combine with command-line options according to
these rules:

- Channels from the metadata and `--channel` flags are merged.
  If the combined list is empty, `conda-forge` is used as the default.
- Conda dependencies from the metadata and `--with` specs are
  merged into a single spec list for the solver.
- PyPI dependencies from `dependencies` are added to the spec list.
  The `conda-pypi` channel is appended automatically when PyPI
  dependencies are present.
- If the script has no metadata block and no `--with`/`--channel`
  flags, conda-exec skips environment creation entirely and runs
  the script with the current Python interpreter.

## File size limit

conda-exec skips metadata parsing for files larger than 10 MB
(`MAX_SCRIPT_SIZE`). Scripts exceeding this limit are treated as having
no metadata block.

## Cache key computation

Script environments use a cache key of the form `script--{hash}`, where
`{hash}` is the first 16 hex characters of the SHA-256 digest computed
from the dependency metadata. The inputs to the hash are:

1. Sorted conda dependencies (joined with `|`)
2. Sorted PyPI dependencies (joined with `|`)
3. Sorted channels (joined with `|`)
4. The `requires-python` value (or empty string if not set)

These four parts are joined with `||` to form the hash input.

The hash is derived from the metadata content, not the file path or
script body. This means:

- Changing only the script code (without changing dependencies) reuses
  the same cached environment.
- Two different scripts with identical dependency declarations share
  the same cached environment.
- Changing any dependency, channel, or the `requires-python` value
  produces a different cache key and a new environment.

## Examples

### Conda dependencies only

```python
# /// script
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["numpy>=1.24", "matplotlib"]
# ///

import numpy as np
import matplotlib.pyplot as plt

data = np.random.randn(1000)
plt.hist(data, bins=30)
plt.savefig("histogram.png")
```

### PyPI dependencies only

Requires conda-pypi to be installed.

```python
# /// script
# dependencies = ["httpx", "rich"]
# ///

import httpx
from rich import print

resp = httpx.get("https://httpbin.org/json")
print(resp.json())
```

### Mixed conda and PyPI dependencies

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich"]
#
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["numpy>=1.24"]
# ///

import numpy as np
from rich import print

print(f"numpy version: {np.__version__}")
```

### Python version constraint only

```python
# /// script
# requires-python = ">=3.12"
# ///

import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text())
print(data["project"]["name"])
```

### No metadata (runs with current Python)

```python
# No metadata block, no dependencies needed
print("Hello from conda exec!")
```

## Compatibility with uv

The standard PEP 723 fields (`requires-python` and `dependencies`) are
compatible with [uv](https://docs.astral.sh/uv/)'s inline script
metadata support. A script using only these fields works with both
`conda exec script.py` and `uv run script.py`.

The `[tool.conda]` extension fields are ignored by uv (and other
PEP 723 consumers), so scripts that include conda-specific
configuration remain valid for other tools. They will simply not
install the conda-specific dependencies.
