# Troubleshoot common issues

```{tip}
Most cache-related problems are fixed by running `conda exec --refresh TOOL ...`,
which discards the cached environment and creates a fresh one. Try this first
before deeper debugging.
```

## "command not found" after install

If `conda exec` is not recognized after installing conda-exec, the plugin
may not be loaded. Verify the installation:

```bash
conda list -n base conda-exec
```

If it is installed but still not found, check that `conda-rattler-solver`
is also installed. conda-exec requires it:

```bash
conda install -n base -c conda-forge conda-rattler-solver
```

The standalone `ce` command should work independently of the plugin system.
If `conda exec` fails but `ce` works, the plugin entry point is not being
discovered. Reinstalling conda-exec usually fixes this:

```bash
conda install -n base -c conda-forge --force-reinstall conda-exec
```

## "solver not available" error

```text
conda exec: conda-rattler-solver is required but not installed
```

Install the solver backend:

```bash
conda install -n base -c conda-forge conda-rattler-solver
```

## "invalid match spec" error

```text
conda exec: invalid match spec for tool '<spec>': <detail>
```

The tool argument is parsed as a conda match spec. Common causes are
unquoted shell characters or invalid conda spec syntax.

Quote version constraints:

```bash
conda exec "ruff>=0.4,<0.5" check .
```

Use `--with` for extra packages instead of appending them to the tool
argument:

```bash
conda exec --with pytest ruff check tests/
```

## "binary not found" error

```text
conda exec: binary 'foo' not found in cached environment
```

The package was installed, but it does not provide a binary matching the
package name. This happens when the package name differs from the
executable name.

Inspect what the package actually provides:

```bash
conda exec --list
```

Check the package contents to find the correct binary name:

```bash
conda search --info foo
```

conda-exec does not currently support installing package `foo` while
running executable `bar` in tool mode. Use a script or a named environment
for that package layout.

## "conda-pypi required" error

```text
conda exec: script declares PyPI dependencies but conda-pypi is not installed
```

Your script has a top-level `dependencies` field (PyPI packages) in its
PEP 723 metadata, but conda-pypi is not available. Install it:

```bash
conda install -n base -c conda-forge conda-pypi
```

Alternatively, move your dependencies to `[tool.conda].dependencies` if
they are available as conda packages, which does not require conda-pypi.

## Slow first run

The first invocation of a tool is slow because conda-exec must:

1. Resolve dependencies using the solver
2. Download packages
3. Extract and install them into the cached environment

Later runs reuse the cache when the dependency input is unchanged. To see
existing cached environments:

```bash
conda exec --list
```

## Cache corruption

If a cached environment is broken (e.g., from an interrupted download or
disk issue), force re-creation:

```bash
conda exec --refresh ruff check .
```

To remove all cached environments and start fresh:

```bash
conda exec --clean --all --yes
```

## Permission denied (exit code 126)

```text
conda exec: ruff: permission denied
```

```{warning}
Re-creating an environment with `--refresh` removes any manual
customizations made to that cached environment. If you have added files
or modified the environment by hand, back them up first.
```

The binary exists but is not executable. This can happen if the cached
environment was copied from another system or if file permissions were
altered. Fix it by re-creating the environment:

```bash
conda exec --refresh ruff check .
```

## Tool not found (exit code 127)

```text
conda exec: ruff: command not found
```

The binary could not be executed. This typically means the executable was
deleted from the cached environment or there is a platform mismatch.
Re-create the environment:

```bash
conda exec --refresh ruff check .
```

If the problem persists, clean the cache entirely:

```bash
conda exec --clean --all --yes
conda exec ruff check .
```

## Stale or unusable script lock data

```text
conda exec: warning: ignoring unusable sidecar lock data: script lock error: <detail>
```

The lockfile was discovered, but conda could not create an environment from
it. If the script still has metadata, conda-exec falls back to solving from
the metadata.

Refresh the lock:

```bash
conda exec --lock --refresh script.py
```

Or bypass the lock for one run:

```bash
conda exec --ignore-lock script.py
```
