# Cache layout

conda-exec stores cached environments under a platform-specific data directory.

## Directory structure

```text
~/.conda/exec/
  run-count                    # automatic cleanup invocation counter
  envs/
    ruff--a3f8b2c1/           # cached env for bare `conda exec ruff`
      conda-meta/
        history               # mtime used for staleness tracking
        created_at            # creation timestamp
        *.json                # package records
      bin/                    # (Unix) or Scripts/ (Windows)
        ruff
    samtools--7e2d9f04/       # different tool, different hash
      ...
    ruff--b9e1c3d7/           # same tool, different specs (e.g. --with pytest)
      ...
    script--c5b9979c/         # cached env for a script with inline deps
      conda-meta/
      bin/
        python
```

Script lockfiles are stored next to scripts, not inside `~/.conda/exec/`:

```text
project/
  script.py
  script.py.conda-exec.lock
```

The exact sidecar name is derived from conda-exec's selected lockfile format.
`script.py.conda-exec.lock` is the default for the `rattler-lock-v6` format.

Embedded lock data lives inside the script in a generated
`# /// conda-exec-lock` block.

## Cache key

### Tool cache key

Each cached tool environment is identified by `{tool}--{hash}` where:

- `tool` is the package name
- `hash` is the first 16 hex characters of the SHA-256 of the normalized, sorted spec list and channel list

Different version constraints, `--with` specs, or `--channel` values produce different cache keys.

### Script cache key

Script environments use the key format `script--{hash}` where `hash` is
derived from the script's dependency metadata:

- Sorted conda dependencies
- Sorted PyPI dependencies
- Sorted channels
- `requires-python` value

The hash is computed from the metadata content, not the file path or
script code. Changing only the code without changing dependencies reuses
the same cached environment. Two different scripts with identical
dependency declarations share the same cached environment.

When a script runs from lock data, the cache key is still `script--{hash}`,
but the hash is derived from the lock content. Updating sidecar or embedded
lock data creates a distinct cached environment.

## Default path

All platforms use `~/.conda/exec/` (alongside conda's own data at `~/.conda/`).

On Windows, `~` expands to `%USERPROFILE%` (typically `C:\Users\<username>`).

## Environment variable override

Set `CONDA_EXEC_HOME` to override the base directory:

```bash
export CONDA_EXEC_HOME=/tmp/conda-exec-test
conda exec ruff check .
# Environment created at /tmp/conda-exec-test/envs/ruff--<hash>/
```

## Staleness tracking

conda-exec uses conda's own `PrefixData` API for staleness tracking:

- `conda-meta/created_at`: records when the environment was created
- `conda-meta/history` mtime: updated on each `conda exec` invocation

The `conda exec --clean` command reads `PrefixData.last_modified` to determine which environments are stale.

Automatic cleanup uses the same staleness data. It stores a best-effort
invocation counter in `~/.conda/exec/run-count` and checks for stale
environments only when the configured interval is reached.
