# Use activation mode

By default, conda-exec only prepends the environment's `bin/` directory to
`PATH`. The `--activate` flag asks conda's activator to compute the
environment variables for the subprocess instead.

## What --activate does

With `--activate`, conda-exec runs conda's activator before executing the
tool. This:

- Sets `CONDA_PREFIX` to the ephemeral environment path
- Exports environment variables reported by conda's activator
- Unsets variables that activation marks for removal

Without `--activate`, only `PATH` is modified.

conda-exec does not execute package `activate.d/` shell scripts. If a tool
requires those scripts, use `conda create` or `conda env create` for a named
environment and run it with
[conda run](https://docs.conda.io/projects/conda/en/stable/commands/run.html)
or an explicitly activated shell. That path matches conda's full shell
activation semantics.

## When you need activation

Some tools check `CONDA_PREFIX`, `CONDA_DEFAULT_ENV`, or other variables
reported by conda's activator. Common cases:

- Bioinformatics pipelines that check `CONDA_PREFIX` to locate data files
- Tools that use the active environment name for configuration
- Scripts that shell out to conda-aware tools

```bash
conda exec --activate -c bioconda snakemake --cores 4
```

## When you do not need activation

```{tip}
Most CLI tools work without activation. If you are running linters,
formatters, or similar standalone tools, skip `--activate` for faster
execution.
```

Most standalone CLI tools only need the binary on `PATH` and work fine
without activation. For example, linters, formatters, and build tools
typically do not inspect `CONDA_PREFIX`:

```bash
conda exec ruff check .
conda exec black --check .
conda exec jq '.name' package.json
```

Skipping activation is the default because it avoids the activation
calculation on every run.

## Performance

Activation adds overhead to each invocation because it imports conda's
activation machinery and computes the activated environment. For tools that
do not need it, omitting `--activate` avoids this cost.

## Example with a script

Activation also works in script mode:

```bash
conda exec --activate script.py
```

The script runs with activation environment variables such as `CONDA_PREFIX`
set, which is useful for scripts that call conda-aware libraries.
