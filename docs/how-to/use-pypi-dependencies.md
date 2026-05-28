# Use PyPI dependencies in scripts

PEP 723 defines top-level `dependencies` as PyPI dependencies. conda-exec
can resolve those dependencies by using `conda-pypi`, which exposes PyPI
packages to conda's solver through the `conda-pypi` channel.

Use this workflow when a script needs a package that is available on PyPI
but is not packaged, not available at the version you need, or not
convenient in your conda channels.

## Install conda-pypi

PyPI dependencies require `conda-pypi` in the environment that provides
`conda exec`:

```bash
conda install -n base -c conda-forge conda-pypi
```

Scripts that only use `[tool.conda].dependencies` do not need
`conda-pypi`.

## Declare PyPI dependencies

Put PyPI package requirements in the standard PEP 723 `dependencies`
field:

```python
# /// script
# dependencies = ["httpx>=0.27", "rich"]
# ///

import httpx
from rich import print

response = httpx.get("https://httpbin.org/json")
print(response.json())
```

Run the script:

```bash
conda exec fetch.py
```

When conda-exec sees top-level `dependencies`, it checks that
`conda-pypi` is importable and appends the `conda-pypi` channel to the
solve.

## Prefer conda packages for conda-native dependencies

If a dependency is available from conda-forge, bioconda, defaults, or
another trusted conda channel, prefer `[tool.conda].dependencies`:

```python
# /// script
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["numpy>=2", "pandas", "pyarrow"]
# ///
```

Conda packages can express non-Python shared libraries, compiled
extensions, run exports, and platform constraints in a way PyPI metadata
cannot always model for conda environments.

Use top-level `dependencies` for packages you intentionally want from PyPI.

## Mix conda and PyPI packages

You can combine both dependency sources in one script:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19", "pysam"]
# ///
```

conda-exec builds one combined spec list:

- `[tool.conda].dependencies`
- top-level PyPI `dependencies`
- any `--with` specs from the command line
- an automatic `python` spec if needed

The resulting environment is solved once for that dependency input, then
cached.

:::{image} ../../demos/pypi-script.gif
:alt: Demo showing a PEP 723 script with mixed PyPI and conda dependencies
:width: 100%
:::

## Pin PyPI dependencies

Use normal PEP 508 requirement strings:

```python
# /// script
# dependencies = [
#   "httpx>=0.27,<0.28",
#   "rich>=13",
# ]
# ///
```

If you need exact repeatability, generate lock data after choosing your
constraints:

```bash
conda exec --lock fetch.py
```

## Set the Python version

Use `requires-python` when PyPI dependencies need a particular Python
range:

```python
# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["httpx", "rich"]
# ///
```

conda-exec translates this to a conda `python` spec for the solve and
validates the resolved interpreter afterwards.

## Add temporary conda packages

Use `--with` for one-off conda packages without editing the script:

```bash
conda exec --with ipython fetch.py
```

This creates a different cached environment because CLI extras are part of
the cache identity. It also bypasses discovered script lock data for that
run because the dependency input has changed.

## Use PyPI scripts in CI

Install the optional integration before running the script:

```yaml
- name: Install conda-exec
  run: conda install -n base -c conda-forge -y conda-exec conda-rattler-solver conda-pypi

- name: Run report script
  run: conda exec scripts/report.py --output report.json
```

For stable CI, prefer bounded version ranges and commit generated lock data:

```bash
conda exec --lock scripts/report.py
```

## Fix missing conda-pypi errors

This error means the script has top-level PyPI dependencies, but
`conda-pypi` is not installed where conda-exec can import it:

```text
conda exec: script declares PyPI dependencies but conda-pypi is not installed
```

Fix it by installing the integration:

```bash
conda install -n base -c conda-forge conda-pypi
```

Or move dependencies to `[tool.conda].dependencies` if you want conda
packages instead of PyPI packages.
