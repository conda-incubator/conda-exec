# Run a script with inline dependencies

This tutorial walks through running a Python script that declares its
dependencies using [PEP 723](https://peps.python.org/pep-0723/) inline
metadata.

## Prerequisites

::::{tab-set}
:::{tab-item} Conda-only scripts

- conda 25.1 or later
- conda-rattler-solver installed
- conda-exec installed (`conda install -c conda-forge conda-exec conda-rattler-solver`)

:::
:::{tab-item} PyPI or mixed scripts

- conda 25.1 or later
- conda-rattler-solver installed
- conda-exec installed (`conda install -c conda-forge conda-exec conda-rattler-solver`)
- conda-pypi installed (`conda install -c conda-forge conda-pypi`)

:::
::::

## Step 1: Write a script with conda dependencies

Create a file called `hello.py`:

```python
# /// script
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["zlib"]
# ///

print("Hello from a conda-exec script!")
```

The `# /// script` and `# ///` markers delimit the metadata block. Inside,
TOML-formatted comments declare the script's dependencies under
`[tool.conda]`.

## Step 2: Run it

```bash
conda exec hello.py
```

On the first run, conda-exec:

1. Detects that `hello.py` is a file (not a package name)
2. Parses the PEP 723 metadata block
3. Solves and creates a cached environment with the declared dependencies
4. Runs the script with `python` from that environment

```text
Creating environment for script... done (4.1s)
Hello from a conda-exec script!
```

Later runs reuse the cached environment when the dependency metadata has
not changed.

:::{image} ../../demos/script-dependencies.gif
:alt: Demo showing conda-exec running a Python script with PEP 723 conda dependencies
:width: 100%
:::

## Step 3: Add PyPI dependencies

conda-exec supports the standard PEP 723 `dependencies` field for PyPI
packages. These are resolved through the
[conda-pypi](https://github.com/conda/conda-pypi) channel,
which requires conda-pypi to be installed.

```{warning}
PyPI dependencies require [conda-pypi](https://github.com/conda/conda-pypi) to be installed. Without it, conda-exec cannot resolve packages from PyPI. Install it with `conda install -c conda-forge conda-pypi`.
```

Create a file called `fetch.py`:

```python
# /// script
# dependencies = ["requests", "rich"]
# ///

import requests
from rich import print

response = requests.get("https://httpbin.org/ip")
print(response.json())
```

```bash
conda exec fetch.py
```

conda-exec adds the `conda-pypi` channel automatically when PyPI
dependencies are declared.

## Step 4: Mix conda and PyPI dependencies

You can combine both dependency sources in one script:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19"]
# ///

import subprocess
import requests

result = subprocess.run(["samtools", "--version"], capture_output=True, text=True)
print(f"samtools: {result.stdout.splitlines()[0]}")
print(f"requests: {requests.__version__}")
```

```bash
conda exec analysis.py
```

All dependencies (conda and PyPI) are resolved together in a single
environment solve.

## Step 5: Pass arguments to the script

Arguments after the script path are passed through:

```bash
conda exec hello.py --verbose output.txt
```

Use `--` to separate conda-exec options from script arguments:

```bash
conda exec --with numpy hello.py -- --flag value
```

## Step 6: Make it directly executable

Add a shebang line so the script can run without typing `conda exec`:

```python
#!/usr/bin/env ce
# /// script
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["zlib"]
# ///

print("Hello from a conda-exec script!")
```

```bash
chmod +x hello.py
./hello.py
```

The `ce` command is the standalone entry point for conda-exec. It works as
a shebang target on all platforms.

## What happened?

conda-exec created a cached environment at
`~/.conda/exec/envs/script--<hash>/`. The cache key is computed from
the script's dependency metadata (not the file path or contents), so
changing only the code without changing the dependencies reuses the same
cached environment.

```{note}
Two scripts with identical dependency metadata share the same cached environment, even if they live in different directories or have different filenames. The cache key depends only on the declared dependencies, channels, and Python version constraint.
```

## Next steps

If this script needs to run repeatably in CI or on another machine, continue
with [Share a locked script](share-locked-script.md).
