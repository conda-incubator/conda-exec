# Your first ephemeral run

This tutorial walks through running a tool with conda-exec for the first time.

## Prerequisites

- conda 25.1 or later
- conda-rattler-solver installed
- conda-exec installed (`conda install conda-exec`)

## Step 1: Run a tool

Let's run `ruff`, a fast Python linter:

```bash
conda exec ruff check .
```

On the first run, conda-exec:

1. Solves the environment (finding `ruff` and its dependencies)
2. Downloads and installs packages into a cache directory
3. Finds the `ruff` binary in the cached environment
4. Runs `ruff check .` and forwards the output

## Step 2: Run it again

```bash
conda exec ruff check .
```

This time it starts instantly because the cached environment already exists.

## Step 3: Try the short alias

```bash
conda x ruff check .
```

`conda x` is an alias for `conda exec`.

## What happened?

conda-exec created a cached environment at `~/.conda/exec/envs/ruff--<hash>/`.
This environment is isolated and disposable. It is not on your PATH and does not affect
your other conda environments.
