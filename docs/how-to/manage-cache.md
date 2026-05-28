# Manage the cache

conda-exec caches environments for reuse. Over time, these caches can
accumulate.

```{tip}
Run `conda exec --list` periodically to see how much disk space cached
environments are using. Each unique combination of tool, version spec, and
channels creates a separate cached environment.
```

## List cached environments

```bash
conda exec --list
```

Shows all cached environments with their size, last-used timestamp, and package count.

For machine-readable output, add `--json`:

```bash
conda exec --list --json
```

See [Cache list JSON](../reference/list-json.md) for the output schema and
empty-cache behavior.

:::{image} ../../demos/cache-management.gif
:alt: Demo showing conda-exec cache listing, JSON output, dry-run cleanup, and cache cleanup
:width: 100%
:::

## Clean old caches

Remove environments not used in 30 days:

```bash
conda exec --clean
```

Preview what would be removed:

```bash
conda exec --clean --dry-run
```

Remove all caches:

```bash
conda exec --clean --all
```

Remove caches for a specific tool:

```bash
conda exec --clean ruff
```

## Automatic cleanup

conda-exec automatically checks for stale cached environments after every
50 successful tool runs. The check removes environments that have not
been used in 30 days and stays silent unless it actually removes
something.

Disable automatic cleanup for one shell:

```bash
export CONDA_EXEC_AUTO_CLEAN=false
```

Change the interval or age:

```bash
export CONDA_EXEC_CLEAN_INTERVAL=25
export CONDA_EXEC_CLEAN_AGE=14
```

For persistent configuration, use conda's plugin settings in `.condarc`:

```yaml
plugins:
  conda_exec_auto_clean: true
  conda_exec_clean_interval: 50
  conda_exec_clean_age: 30
```

See [Configure automatic cleanup](configure-cleanup.md) for workstation,
CI, and scratch-directory examples.

## Force re-creation

```{note}
The `--refresh` flag only affects the specific tool and spec combination
you pass. Other cached environments are left untouched.
```

If a cached environment is stale or broken, force re-creation:

```bash
conda exec --refresh ruff check .
```

For script lock data, `--refresh` also bypasses discovered locks and solves
from the script metadata for that run.
