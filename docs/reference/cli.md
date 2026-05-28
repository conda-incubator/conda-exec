# CLI reference

## conda exec

Run a command from a conda package or a Python script without installing
dependencies permanently.

### Synopsis

::::{tab-set}
:::{tab-item} conda exec

```text
conda exec [OPTIONS] TOOL [TOOL_ARGS...]
conda exec [OPTIONS] SCRIPT.py [SCRIPT_ARGS...]
conda exec --list [--json]
conda exec --clean [OPTIONS] [TOOL]
```

:::
:::{tab-item} ce (standalone alias)

```text
ce [OPTIONS] TOOL [TOOL_ARGS...]
ce [OPTIONS] SCRIPT.py [SCRIPT_ARGS...]
ce --list [--json]
ce --clean [OPTIONS] [TOOL]
```

:::
::::

### Options

`-c, --channel CHANNEL`
: Additional channel to search (repeatable). Default: `conda-forge`.

`--with MATCHSPEC`
: Additional package to install in the ephemeral environment (repeatable). Values are full match specs. Example: `--with pytest --with "python=3.12"`.

`--activate`
: Apply conda activation environment variables before running the tool. Sets `CONDA_PREFIX` and other activation variables, but does not run `activate.d` shell scripts. Most tools do not need this; use it for tools that depend on conda activation env vars.

`--refresh`
: Force re-creation of the cached environment.

`--lock`
: Generate lock data for a script environment. Script-only.

`--embed`
: Embed generated lock data in the script instead of writing a sidecar
  lockfile. Requires `--lock`.

`--ignore-lock`
: Ignore discovered script lock data and solve from script metadata.

`--platform SUBDIR`
: Platform/subdir to include when writing lock data (repeatable). Examples:
  `linux-64`, `osx-arm64`, `win-64`. Only used with `--lock`.

`--list`
: Show all cached environments (mutually exclusive with `--clean`).

`--clean`
: Remove cached environments (mutually exclusive with `--list`).

### Arguments

`TOOL`
: Package to run, as a name or full match spec (e.g. `ruff` or `ruff>=0.4`). The binary name is extracted from the match spec automatically. If the argument is a path to an existing file, conda-exec runs it as a Python script instead (see [Script mode](#script-mode) below).

  See [Package specs](package-specs.md) for accepted match spec forms,
  quoting rules, channel behavior, and cache identity.

`TOOL_ARGS`
: Arguments passed through to the tool or script. Use `--` to separate conda-exec options from tool options.

```{note}
If the tool's arguments start with dashes (e.g. `--config`), conda-exec may
try to interpret them as its own flags. Place a `--` separator between
conda-exec options and the tool's arguments to avoid this:

    conda exec ruff -- --config pyproject.toml check .
```

### Examples

```bash
# Basic usage
conda exec ruff check .
ce ruff check .

# Version constraint (match spec as the tool argument)
conda exec "ruff>=0.4,<0.5" check .

# Extra packages
conda exec --with pytest ruff check .

# Custom channel
conda exec -c bioconda samtools view file.bam

# Force re-creation
conda exec --refresh ruff check .

# Activation environment variables (sets CONDA_PREFIX, etc.)
conda exec --activate samtools view file.bam

# Separate tool args with --
conda exec ruff -- --config pyproject.toml check .
```

(script-mode)=

## Script mode

When the `TOOL` argument is a path to an existing file, conda-exec runs
it as a Python script. If the script contains a
[PEP 723](https://peps.python.org/pep-0723/) metadata block, conda-exec
parses the declared dependencies and creates a cached environment for them.

### Metadata format

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

`requires-python`
: Python version constraint (optional). Translated to a `python` spec
  in the environment solve.

```{warning}
Scripts that declare top-level `dependencies` (PyPI packages) require
[conda-pypi](https://github.com/conda/conda-pypi) to be installed.
If conda-pypi is missing, conda-exec raises a `PyPIDependencyError`. Scripts
that only use `[tool.conda].dependencies` do not need conda-pypi.
```

`dependencies`
: PyPI package dependencies (PEP 723 standard field). Requires
  [conda-pypi](https://github.com/conda/conda-pypi)
  to be installed. The `conda-pypi` channel is added automatically.

`[tool.conda].dependencies`
: Conda package dependencies as match specs.

`[tool.conda].channels`
: Conda channels to search. Defaults to `conda-forge` if not specified.

### Script examples

```bash
# Run a script with inline deps
conda exec script.py

# Pass arguments to the script
conda exec script.py --verbose output.txt

# Separate conda-exec options from script args
conda exec --with numpy script.py -- --flag value

# Force re-creation of the script environment
conda exec --refresh script.py

# Generate sidecar lock data
conda exec --lock script.py

# Embed lock data into the script
conda exec --lock --embed script.py

# Generate lock data for multiple platforms
conda exec --lock --platform linux-64 --platform osx-arm64 script.py

# Script without metadata (runs with current Python)
conda exec hello.py
```

### Script lock data

`conda exec --lock script.py`
: Resolves the script environment and writes a sidecar lockfile using
  conda-exec's default sidecar name for the selected lockfile format. With
  the default `rattler-lock-v6` format, this is
  `script.py.conda-exec.lock`.

`conda exec --lock --embed script.py`
: Resolves the script environment and writes a generated
  `# /// conda-exec-lock` block into `script.py`.

`conda exec script.py`
: Uses embedded lock data first, then a sidecar lockfile, then falls back to
  solving from PEP 723 metadata when no matching lock data is available.

`conda exec --refresh script.py`
: Ignores lock data and solves from metadata.

`conda exec --ignore-lock script.py`
: Ignores discovered lock data for one run and solves from metadata.

`--lock` is only supported for scripts. `--embed` requires `--lock`.

See [Script lock reference](script-locks.md) for sidecar discovery names,
embedded block syntax, digest matching, and lock cache keys.

## conda exec --list

Show all cached environments.

```text
conda exec --list [--json]
```

`--json`
: Output as JSON instead of a table.

```bash
conda exec --list
```

See [Cache list JSON](list-json.md) for the exact JSON fields.

```text
Tool        Size     Last used         Packages
ruff       42.9 MB   2 days ago        3
samtools  114.4 MB   5 hours ago       47
```

## conda exec --clean

Remove cached environments.

```text
conda exec --clean [--all] [--older-than DAYS] [--dry-run] [-y/--yes] [TOOL]
```

`--all`
: Remove all matching environments regardless of age.

`--older-than DAYS`
: Only remove environments not used in the last DAYS days (default: 30).

`--dry-run`
: Show what would be removed without actually removing anything.

`-y, --yes`
: Skip confirmation prompt.

`TOOL`
: Only clean environments for this tool (optional).

```bash
# Remove environments unused for 30+ days (with confirmation)
conda exec --clean

# Preview what would be removed
conda exec --clean --dry-run

# Remove everything, no prompt
conda exec --clean --all --yes

# Remove only ruff caches older than 7 days
conda exec --clean --older-than 7 ruff
```
