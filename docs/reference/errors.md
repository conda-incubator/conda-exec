# Error messages

All error conditions raised by conda-exec, with their messages, hints,
and exit codes.

## Exit codes

| Code  | Meaning |
|-------|---------|
| 0     | Success |
| 1     | conda-exec error (solve failure, binary not found, missing dependency, etc.) |
| 2     | Usage error (missing required arguments) |
| 126   | Permission denied when executing the tool binary |
| 127   | Tool binary not found at the expected path |
| Other | Forwarded from the tool's own exit code |

When a tool runs successfully, conda-exec returns whatever exit code
the tool itself returns. The codes 1, 2, 126, and 127 are reserved
for conda-exec's own error conditions.

## Solve and environment errors

### SolveError

Raised when the conda solver cannot resolve the requested packages.

```text
conda exec: failed to solve environment for '<tool>': <detail>
```

The `<detail>` portion contains the solver's own error message,
which typically lists conflicting constraints. Common causes include
version specs that no package satisfies, or conflicting requirements
between `--with` specs.

### SolverNotAvailableError

Raised when no solver backend is available.

```text
conda exec: conda-rattler-solver is required but not installed
  hint: install it with: conda install -n base conda-rattler-solver
  hint: or set 'solver: rattler' in your .condarc
```

### BinaryNotFoundError

Raised when the environment was created successfully but does not
contain an executable matching the tool name.

```text
conda exec: binary '<tool>' not found in cached environment
  hint: the package may not provide a '<tool>' executable
  hint: check the package contents with 'conda search --info <package>'
```

This can happen when the package name differs from the executable it
provides. For example, a package named `python-black` might install a
binary called `black`.

### PyPIDependencyError

Raised in script mode when the script declares top-level `dependencies`
(PyPI packages) but conda-pypi is not installed.

```text
conda exec: script declares PyPI dependencies but conda-pypi is not installed
  hint: install it with: conda install -n base conda-pypi
  hint: or remove the top-level 'dependencies' from the script metadata
```

### PythonVersionError

Raised when a script's `requires-python` constraint cannot be
satisfied by the Python version in the environment.

```text
conda exec: script requires Python <required>, but the environment has <available>
```

## Execution errors

These errors occur after the environment is ready, when conda-exec
attempts to run the tool binary.

### Command not found (exit 127)

The binary path exists in the cache but the OS cannot find it at
execution time.

```text
conda exec: <name>: command not found
```

### Permission denied (exit 126)

The binary exists but lacks execute permission.

```text
conda exec: <name>: permission denied
```

## Usage errors

### Missing TOOL argument (exit 2)

No tool or script was specified and no mode flag (`--list`, `--clean`)
was given.

```text
conda exec: missing TOOL argument
usage: conda exec [OPTIONS] TOOL [ARGS...]
       conda exec --list
       conda exec --clean
```

## Warnings

These are non-fatal messages printed to stderr. They do not affect the
exit code.

### Misplaced --json flag

`--json` was passed without `--list`.

```text
conda exec: warning: --json is only used with --list
```

### Misplaced --dry-run flag

`--dry-run` was passed without `--clean`.

```text
conda exec: warning: --dry-run is only used with --clean
```

### Unclosed script metadata block

A `# /// script` marker was found but no closing `# ///` was reached
before end of file.

```text
conda exec: warning: unclosed '# /// script' block
```

### Failed metadata parse

The inline metadata block was found but contains invalid TOML.

```text
conda exec: failed to parse inline metadata: <parse error>
```
