# Your first ephemeral run

This tutorial walks through running a tool with conda-exec for the first time.

## Prerequisites

- conda 25.1 or later
- conda-rattler-solver installed
- conda-exec installed (`conda install -c conda-forge conda-exec conda-rattler-solver`)

## Step 1: Run a tool

Run `ruff`, a fast Python linter:

::::{tab-set}
:::{tab-item} conda exec

```bash
conda exec ruff check .
```

:::
:::{tab-item} ce (standalone)

```bash
ce ruff check .
```

:::
::::

On the first run, you will see a progress message while the environment is created:

```text
Creating environment for ruff... done (3.2s)
```

conda-exec:

1. Solves the environment (finding `ruff` and its dependencies)
2. Downloads and installs packages into a cache directory
3. Finds the `ruff` binary in the cached environment
4. Runs `ruff check .` and forwards the output

## Step 2: Run it again

```bash
conda exec ruff check .
```

This time there is no creation message because the cached environment
already exists.

## Step 3: Try the standalone alias

```bash
ce ruff check .
```

`ce` is a standalone command that works the same as `conda exec`.

```{tip}
Run `conda exec --list` to see all cached environments and their sizes.
```

## What happened?

conda-exec created a cached environment at `~/.conda/exec/envs/ruff--<hash>/`.
This environment is isolated and disposable. It is not on your PATH and does not affect
your other conda environments.

## Next steps

conda-exec can also run Python scripts with inline dependency metadata.
See the [Run a script](run-script.md) tutorial to learn how.
