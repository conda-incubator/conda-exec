# Environment variables

Environment variables that conda-exec reads, sets, or respects during operation.

## conda-exec variables

`CONDA_EXEC_HOME`
: Override the base data directory for cached environments.
  Default: `~/.conda/exec/`. Must be an absolute path (or a path starting
  with `~`, which is expanded). When set, all cached environments are
  stored under `$CONDA_EXEC_HOME/envs/` instead of `~/.conda/exec/envs/`.
  Useful for testing or placing the cache on a different filesystem.

  ```bash
  export CONDA_EXEC_HOME=/scratch/conda-exec
  conda exec ruff check .
  # Environment stored at /scratch/conda-exec/envs/ruff--<hash>/
  ```

## Variables set during tool execution

`PATH`
: Modified before the tool process starts. The behavior depends on the
  `--activate` flag:

  - Without `--activate` (default): the prefix's `bin/` directory
    (or `Scripts/` on Windows) is prepended to `PATH`. No other
    environment variables are changed.

  - With `--activate`: conda's activator computes the subprocess
    environment, which modifies `PATH` and may set or unset additional
    variables (see `CONDA_PREFIX` below).

`CONDA_PREFIX`
: Only set when `--activate` is used. Points to the ephemeral
  environment prefix (e.g. `~/.conda/exec/envs/samtools--7e2d9f04/`).
  Without `--activate`, this variable is not set.

## Standard conda variables

conda-exec runs within conda's plugin framework and inherits conda's
context system. The following standard conda environment variables are
respected through `conda.base.context`:

`CONDA_ALWAYS_YES`
: When set to `true`, skip confirmation prompts (equivalent to
  `--yes` on the command line). Applies to `conda exec --clean`.

`CONDA_DRY_RUN`
: When set to `true`, report what would be done without making
  changes. Applies to `conda exec --clean`.

`CONDA_JSON`
: When set to `true`, produce JSON output. Applies to
  `conda exec --list`.

`CONDA_SUBDIR`
: Override the platform subdirectory used for package resolution
  (e.g. `linux-64`, `osx-arm64`). Passed through to the solver.

## Path resolution order

The base data directory is resolved in this order:

1. `CONDA_EXEC_HOME` environment variable, if set
2. `~/.conda/exec/` (primary location on all platforms)
3. On Windows only, if `~/.conda/exec/` does not exist:
   `platformdirs.user_data_dir("conda", "conda") / "exec"` as a
   fallback matching conda's own data directory conventions
