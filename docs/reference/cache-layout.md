# Cache layout

conda-exec stores cached environments under a platform-specific data directory.

## Directory structure

```text
~/.conda/exec/
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
```

## Cache key

Each cached environment is identified by `{tool}--{hash}` where:

- `tool` is the package name
- `hash` is the first 16 hex characters of the SHA-256 of the normalized, sorted spec list and channel list

Different version constraints, `--with` specs, or `--channel` values produce different cache keys.

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
