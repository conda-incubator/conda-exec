# How caching works

conda-exec creates isolated conda environments on demand and reuses them
across invocations. The cache is keyed by dependency input, so reuse is
deterministic rather than tied to a project directory or shell session.

## Cache key computation

Every cached environment is identified by a deterministic key of the form
`{tool}--{hash16}`. The hash is the first 16 hex characters of a SHA-256
digest computed from the sorted, normalized specs and channels.

For tool invocations (`conda exec ruff check .`), the key is built from three inputs:

1. The tool name (the package name extracted from the spec)
2. All package specs, including `--with` extras, sorted and normalized through {py:class}`~conda.models.match_spec.MatchSpec`
3. The sorted channel list

The normalization step is important. `ruff>=0.4` and `ruff >=0.4`
produce the same {py:class}`~conda.models.match_spec.MatchSpec` string, so
they produce the same hash and share one environment. However, `ruff>=0.4`
and `ruff>=0.5` produce different hashes. Two invocations with different
specs for the same tool always get separate environments.

The hash blob is constructed as:

```
{sorted normalized specs joined by |}||{sorted channels joined by |}
```

For example, `conda exec ruff --with black -c conda-forge` produces a blob
like `black|ruff||conda-forge`, which is then SHA-256 hashed.

### Script cache keys

Scripts use a different key scheme: `script--{hash16}`. The hash is
computed from the script's metadata rather than its file path or code:

- Sorted conda dependencies
- Sorted PyPI dependencies
- Sorted channels
- The `requires-python` constraint (or empty string if absent)

If you edit a script's code without changing its dependency block,
conda-exec reuses the existing environment. Changes to the `# /// script`
metadata create a new cache key.

```{note}
Because script cache keys are derived from metadata rather than file content,
two different scripts with identical dependency blocks share the same cached
environment. This is intentional and avoids redundant solves.
```

When a script runs from lock data, the key is still `script--{hash16}`, but
the hash input is the lock content. That means refreshing lock data creates
a new cached prefix even when the human-authored metadata stays the same.

## Cache directory layout

Cached environments live under `~/.conda/exec/envs/`. Each environment is a
standard conda prefix directory:

```
~/.conda/exec/
  envs/
    ruff--a1b2c3d4e5f6g7h8/
      bin/
        ruff
      conda-meta/
        history
        ruff-0.4.1-py312h...json
        ...
    black--9f8e7d6c5b4a3210/
      ...
    script--f1e2d3c4b5a69870/
      ...
```

The `conda-meta/` subdirectory serves double duty. It marks the environment
as valid (both `get_or_create` and `exists` check for its presence) and it
stores package records that conda's
{py:class}`~conda.core.prefix_data.PrefixData` can read for the `--list`
command.

## Atomic environment creation

Creating a conda environment involves downloading and extracting packages,
which can fail partway through. A partially extracted environment must not
be visible as a valid cache entry.

conda-exec prevents this with a three-step creation pattern:

1. Create a temporary directory in the envs directory using `tempfile.mkdtemp` (prefixed with `.tmp-`)
2. Solve dependencies and extract packages into this temporary prefix
3. Rename the temporary directory to the final cache key path

Because a same-filesystem rename is atomic, no other process can observe a
half-built environment at the final path. If the solve or extraction fails,
the temporary directory is cleaned up with `rm_rf`.

There is one edge case worth understanding: concurrent creation. If two
processes try to create the same environment simultaneously, both may solve
independently, but only one rename succeeds. The other process checks
whether the final path now exists with a valid `conda-meta/` directory. If
it does, the temporary copy is discarded and the existing environment is
used. If the final path still does not exist, the error is re-raised.

## Cache hits and misses

The `get_or_create` method implements the fast path:

1. Compute the prefix path from the cache key
2. Check if the directory exists and contains a `conda-meta/` subdirectory (two `stat` calls)
3. If yes: touch the history file for staleness tracking, return the prefix
4. If no: run the full solver and transaction pipeline

Cache existence checks deliberately avoid loading
{py:class}`~conda.core.prefix_data.PrefixData`. Calling `PrefixData` means
reading and parsing every JSON record in `conda-meta/`, which adds
measurable latency for large environments. The cache-hit path only checks
for the prefix directory and `conda-meta/`.

{py:class}`~conda.core.prefix_data.PrefixData` is only used in the `--list`
command, where the metadata (package count, creation time, size) is
actually needed.

## Staleness tracking

conda-exec uses the `conda-meta/history` file's mtime (modification time)
to track when an environment was last used. Cache hits call `touch()` on
this file.

To avoid excessive filesystem writes on tools that run frequently (linters in editor save hooks, formatters in CI loops), the touch operation includes a 1-hour debounce. If the history file was modified less than 3600 seconds ago, the touch is skipped entirely.

```{tip}
The 1-hour debounce means that running `conda exec ruff` hundreds of times
per hour (e.g. from an editor on-save hook) produces at most one filesystem
write for staleness tracking. This keeps the overhead of cache hits minimal
even under heavy use.
```

The `--clean` command reads these mtimes through
{py:attr}`~conda.core.prefix_data.PrefixData.last_modified` to determine
which environments are stale. An environment that has not been used in a
configurable number of days can be removed to reclaim disk space.

Automatic cleanup uses the same staleness data and an invocation counter.
See [Configure automatic cleanup](../how-to/configure-cleanup.md) for the
user-facing controls.

## The CONDA_EXEC_HOME override

By default, conda-exec stores everything under `~/.conda/exec/`. The
`CONDA_EXEC_HOME` environment variable overrides this base path entirely.
This is useful for:

- Testing: point to a temporary directory so tests do not pollute the user's real cache
- Custom layouts: place the cache on a faster disk or a shared filesystem
- CI environments: use an ephemeral directory that is discarded after the job

On Windows, if `~/.conda/exec/` does not exist, conda-exec falls back to
`platformdirs.user_data_dir("conda", "conda") / "exec"`, matching conda's
own convention.

## Validation and safety

Cache keys are validated at multiple levels to prevent misuse:

- Tool names must match `SAFE_TOOL_RE`: alphanumeric characters, hyphens, underscores, dots, and plus signs. Names must start with an alphanumeric character or underscore. Empty names and names longer than 128 characters are rejected.
- Full cache keys must match `SAFE_KEY_RE`: a valid tool name, followed by `--`, followed by hex digits.
- `prefix_for()` resolves the constructed path and checks `is_relative_to()` against the envs directory. A key containing `../` or other traversal sequences will be caught even if it passes the regex, because the resolved path will escape the envs directory.
- Keys longer than 200 characters are rejected to prevent filesystem issues on platforms with path length limits.

These checks are defense-in-depth. The `cache_key()` method constructs keys from validated tool names and hex digests, so the regex and path checks should never fail in normal operation. They exist to catch programming errors and to harden against unexpected inputs if the validation surface is ever extended.
