# Run scripts with dependencies

conda-exec can run Python scripts that declare their dependencies inline
using the [PEP 723](https://peps.python.org/pep-0723/) metadata format.

## Conda-only dependencies

Use the `[tool.conda]` table to declare conda packages:

```python
# /// script
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19", "htslib"]
# ///
```

```bash
conda exec script.py
```

## PyPI dependencies

Use the standard PEP 723 `dependencies` field for PyPI packages:

```python
# /// script
# dependencies = ["requests>=2.31", "rich"]
# ///
```

```bash
conda exec script.py
```

```{warning}
PyPI dependencies require [conda-pypi](https://github.com/conda/conda-pypi)
to be installed. Without it, conda-exec cannot resolve PyPI packages and will
exit with an error.
```

conda-exec adds the `conda-pypi` channel automatically.

Install conda-pypi if you haven't already:

```bash
conda install -n base conda-pypi
```

## Mixed conda and PyPI dependencies

Combine both in a single script:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19"]
# ///
```

Both conda and PyPI packages are resolved together in a single environment
solve. The `conda-pypi` channel converts PyPI wheels into conda packages,
so the rattler solver handles everything in one pass.

## Pin the Python version

Use `requires-python` to constrain which Python version is installed:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["click"]
# ///
```

This adds a `python >=3.12` spec to the environment solve.

## Add extra dependencies from the CLI

Override or extend a script's dependencies from the command line:

```bash
conda exec --with numpy -c defaults script.py
```

CLI extras (`--with` and `-c`) are merged with the script's declared
dependencies.

## Scripts without metadata

```{note}
Scripts without a `# /// script` block run directly with the current
Python interpreter. No environment is created, and no packages are installed.
```

Scripts without metadata are passed through as-is:

```bash
conda exec hello.py
```

## Make scripts directly executable

Add a shebang line to run scripts without typing `conda exec` or `ce`:

```python
#!/usr/bin/env ce
# /// script
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["numpy"]
# ///

import numpy as np
print(np.random.default_rng().random(5))
```

```bash
chmod +x demo.py
./demo.py
```

The `ce` standalone command is the recommended shebang target because it
works on all platforms. Using `conda exec` in a shebang does not work
because the kernel cannot split multi-word interpreter arguments portably.

```{note}
On macOS and recent Linux kernels, `#!/usr/bin/env -S conda exec` works
via the `-S` (split string) flag, but this is not portable to all systems.
Use `#!/usr/bin/env ce` for maximum compatibility.
```

## Force re-creation

If the cached script environment is stale:

```bash
conda exec --refresh script.py
```
