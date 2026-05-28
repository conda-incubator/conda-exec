# Configure automatic cleanup

conda-exec keeps cached environments for reuse. Automatic cleanup prevents
old entries from accumulating when users do not run `conda exec --clean`
manually.

Automatic cleanup is best effort. It runs only after successful tool or
script executions, stays silent when nothing is removed, and never runs
during `--list` or `--clean`.

## See the defaults

By default, conda-exec:

- checks after every 50 successful runs
- removes environments not used in 30 days
- keeps automatic cleanup enabled

The invocation counter is stored at `~/.conda/exec/run-count`, or under
`$CONDA_EXEC_HOME/run-count` when `CONDA_EXEC_HOME` is set.

## Disable cleanup for one shell

Set `CONDA_EXEC_AUTO_CLEAN=false`:

```bash
export CONDA_EXEC_AUTO_CLEAN=false
```

Accepted false values are `0`, `false`, `no`, and `off`. Accepted true
values are `1`, `true`, `yes`, and `on`.

## Change the interval

Run cleanup checks more or less often with `CONDA_EXEC_CLEAN_INTERVAL`.
The value must be a positive integer:

```bash
export CONDA_EXEC_CLEAN_INTERVAL=10
```

A lower interval reclaims space sooner. A higher interval does less cache
bookkeeping on machines that run conda-exec frequently.

## Change the stale age

Set how old an environment must be before automatic cleanup removes it:

```bash
export CONDA_EXEC_CLEAN_AGE=7
```

The value is measured in days and must be zero or greater. A value of `0`
means an environment is eligible once its last-used timestamp is older than
the current moment. In practice, the one-hour staleness touch debounce means
recently used environments are still protected from immediate churn.

## Configure persistently in .condarc

Use conda plugin settings in
[`.condarc`](https://docs.conda.io/projects/conda/en/stable/user-guide/configuration/use-condarc.html)
for persistent configuration:

```yaml
plugins:
  conda_exec_auto_clean: true
  conda_exec_clean_interval: 50
  conda_exec_clean_age: 30
```

The direct `CONDA_EXEC_*` environment variables override these settings for
the current process.

## Configure CI runners

On ephemeral hosted CI runners, automatic cleanup usually does not matter
because the machine is discarded. You can disable it to avoid background
cache decisions during short jobs:

```bash
export CONDA_EXEC_AUTO_CLEAN=false
```

On self-hosted runners, keep automatic cleanup enabled and use a shorter
age:

```bash
export CONDA_EXEC_CLEAN_INTERVAL=10
export CONDA_EXEC_CLEAN_AGE=7
```

You can still do an explicit cleanup at the end of a job:

```bash
conda exec --clean --older-than 7 --yes
```

## Pair cleanup with a custom cache location

If you store conda-exec caches on scratch storage, configure both the home
directory and cleanup policy together:

```bash
export CONDA_EXEC_HOME=/scratch/$USER/conda-exec
export CONDA_EXEC_CLEAN_INTERVAL=20
export CONDA_EXEC_CLEAN_AGE=3
```

All cached environments then live under `$CONDA_EXEC_HOME/envs/`, and the
automatic cleanup counter lives under `$CONDA_EXEC_HOME/run-count`.

## Use manual cleanup for one-off pruning

Automatic cleanup is intentionally conservative. Use manual cleanup when you
want an immediate result:

```bash
conda exec --clean --dry-run
conda exec --clean --older-than 14
conda exec --clean --all --yes
```

See [Manage the cache](manage-cache.md) for the full cleanup workflow.
