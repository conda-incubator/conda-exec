# Use in CI/CD pipelines

conda-exec lets CI jobs run tools from conda packages without adding those
tools to the project environment.

## Install conda-exec

Install conda-exec and its solver dependency into the base environment:

```bash
conda install -n base -c conda-forge conda-exec conda-rattler-solver
```

The standalone `ce` command is also available after installation:

```bash
ce ruff check .
```

## Run tools without permanent installation

Instead of adding linters, formatters, or other tools to your project's
environment, run them ephemerally:

```bash
conda exec ruff check .
conda exec black --check src/
conda exec mypy src/
```

Each tool gets its own isolated environment. Nothing is installed into your
project's conda environment.

## Non-interactive mode

The `--clean` subcommand prompts for confirmation by default. In CI, pass
`-y` or `--yes` to skip the prompt:

```bash
conda exec --clean --all --yes
```

Other subcommands (`conda exec TOOL`, `--list`, `--refresh`) do not prompt
and work in CI without extra flags.

## Cache persistence

```{tip}
Caching the conda-exec environment directory between CI runs avoids solving
and downloading the same tool environment repeatedly.
```

conda-exec stores cached environments in `~/.conda/exec/envs/`. To speed
up CI runs, cache this directory between jobs.

::::{tab-set}
:::{tab-item} GitHub Actions

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.conda/exec/envs
    key: conda-exec-${{ runner.os }}
```

:::

:::{tab-item} Generic CI
Cache the directory `~/.conda/exec/envs` using your CI provider's cache
mechanism. The key should include the OS to avoid cross-platform conflicts.

If your CI supports a `save`/`restore` cache step:

```bash
# restore
cp -a /cache/conda-exec-envs ~/.conda/exec/envs 2>/dev/null || true

# ... run your jobs ...

# save
cp -a ~/.conda/exec/envs /cache/conda-exec-envs
```

:::
::::

With caching enabled, only the first CI run for a given cache key resolves
and downloads packages. Later runs reuse the cached environments.

## Example: GitHub Actions workflow

A complete workflow that uses conda-exec for linting:

```yaml
name: Lint
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: conda-incubator/setup-miniconda@v3
        with:
          activate-environment: ""
          auto-activate-base: true

      - name: Install conda-exec
        run: conda install -n base -c conda-forge -y conda-exec conda-rattler-solver

      - uses: actions/cache@v4
        with:
          path: ~/.conda/exec/envs
          key: conda-exec-${{ runner.os }}

      - name: Lint
        run: conda exec ruff check .

      - name: Format check
        run: conda exec black --check src/
```

## Run scripts with inline dependencies

CI jobs can run Python scripts that declare their own dependencies, without
any prior setup beyond conda-exec itself:

```bash
conda exec analysis.py --output results.json
```

The script's [PEP 723](https://peps.python.org/pep-0723/) metadata block
tells conda-exec exactly which packages to install.

## Clean up after CI

To free disk space at the end of a CI job (useful on self-hosted runners):

```bash
conda exec --clean --all --yes
```

## Override the cache directory

Set `CONDA_EXEC_HOME` to control where cached environments are stored:

```bash
export CONDA_EXEC_HOME=/tmp/conda-exec-cache
conda exec ruff check .
```

This is useful when the CI runner's home directory is not suitable for
caching.
