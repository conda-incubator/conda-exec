# CLI reference

## conda exec / conda x

Run a command from a conda package without installing it permanently.

### Synopsis

```
conda exec [OPTIONS] TOOL [TOOL_ARGS...]
conda x [OPTIONS] TOOL [TOOL_ARGS...]
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

### Arguments

`TOOL`
: Package to run, as a name or full match spec (e.g. `ruff` or `ruff>=0.4`). The binary name is extracted from the match spec automatically. Use `list` to show cached environments or `clean` to remove them.

`TOOL_ARGS`
: Arguments passed through to the tool. Use `--` to separate conda-exec options from tool options.

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

## conda exec list

Show all cached environments.

```text
conda exec list [--json]
```

`--json`
: Output as JSON instead of a table.

```bash
conda exec list
```

```text
Tool       Key                        Size      Packages  Last used
ruff       ruff--a3f8b2c1d9e0f4a7     42.9 MB   3         2 days ago
samtools   samtools--7e2d9f04b1c3e8   114.4 MB  47         5 hours ago
```

## conda exec clean

Remove cached environments.

```text
conda exec clean [--all] [--older-than DAYS] [--dry-run] [-y/--yes] [TOOL]
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
conda exec clean

# Preview what would be removed
conda exec clean --dry-run

# Remove everything, no prompt
conda exec clean --all --yes

# Remove only ruff caches older than 7 days
conda exec clean --older-than 7 ruff
```
