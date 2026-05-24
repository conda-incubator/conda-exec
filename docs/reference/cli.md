# CLI reference

## conda exec / conda x

Run a command from a conda package or a Python script without installing
dependencies permanently.

### Synopsis

```text
conda exec [OPTIONS] TOOL [TOOL_ARGS...]
conda exec [OPTIONS] SCRIPT.py [SCRIPT_ARGS...]
conda x [OPTIONS] TOOL [TOOL_ARGS...]
conda exec --list [--json]
conda exec --clean [OPTIONS] [TOOL]
```

### Options

`-c, --channel CHANNEL`
: Additional channel to search (repeatable). Default: `conda-forge`.

`--with MATCHSPEC`
: Additional package to install in the ephemeral environment (repeatable). Values are full match specs. Example: `--with pytest --with "python=3.12"`.

`--activate`
: Activate the environment before running the tool. Sets `CONDA_PREFIX` and other activation variables. Most tools do not need this; use it for tools that depend on conda activation env vars.

`--refresh`
: Force re-creation of the cached environment.

`--list`
: Show all cached environments (mutually exclusive with `--clean`).

`--clean`
: Remove cached environments (mutually exclusive with `--list`).

### Arguments

`TOOL`
: Package to run, as a name or full match spec (e.g. `ruff` or `ruff>=0.4`). The binary name is extracted from the match spec automatically. If the argument is a path to an existing file, conda-exec runs it as a Python script instead (see [Script mode](#script-mode) below).

`TOOL_ARGS`
: Arguments passed through to the tool or script. Use `--` to separate conda-exec options from tool options.

### Examples

```bash
# Basic usage
conda exec ruff check .
conda x ruff check .

# Version constraint (match spec as the tool argument)
conda exec "ruff>=0.4,<0.5" check .

# Extra packages
conda exec --with pytest ruff check .

# Custom channel
conda exec -c bioconda samtools view file.bam

# Force re-creation
conda exec --refresh ruff check .

# Full activation (sets CONDA_PREFIX, etc.)
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

`dependencies`
: PyPI package dependencies (PEP 723 standard field). Requires
  [conda-pypi](https://github.com/conda-incubator/conda-pypi)
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

# Script without metadata (runs with current Python)
conda exec hello.py
```

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

```text
Tool       Key                        Size      Packages  Last used
ruff       ruff--a3f8b2c1d9e0f4a7     42.9 MB   3         2 days ago
samtools   samtools--7e2d9f04b1c3e8   114.4 MB  47         5 hours ago
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
