# Use activation mode

By default, conda-exec only prepends the environment's `bin/` directory to
`PATH`. The `--activate` flag applies full conda activation instead.

## What --activate does

With `--activate`, conda-exec runs conda's activation logic before executing
the tool. This:

- Sets `CONDA_PREFIX` to the ephemeral environment path
- Exports environment variables defined by activation scripts (e.g.
  `JAVA_HOME`, `R_HOME`)
- Unsets variables that activation marks for removal
- Applies any `activate.d/` scripts bundled with installed packages

Without `--activate`, only `PATH` is modified.

## When you need activation

Some tools check `CONDA_PREFIX` or rely on environment variables that
conda packages set through activation scripts. Common cases:

- R packages that need `R_HOME`
- Java tools that need `JAVA_HOME`
- Bioinformatics pipelines that check `CONDA_PREFIX` to locate data files
- Tools that use `CONDA_DEFAULT_ENV` for configuration

```bash
conda exec --activate -c bioconda snakemake --cores 4
```

## When you do not need activation

Most standalone CLI tools only need the binary on `PATH` and work fine
without activation. For example, linters, formatters, and build tools
typically do not inspect `CONDA_PREFIX`:

```bash
conda exec ruff check .
conda exec black --check .
conda exec jq '.name' package.json
```

Skipping activation is the default because it is faster.

## Performance

Activation adds overhead to each invocation. It imports conda's activation
machinery and processes activation scripts from installed packages. For
tools that do not need it, omitting `--activate` avoids this cost.

## Example with a script

Activation also works in script mode:

```bash
conda exec --activate script.py
```

The script runs inside a fully activated environment with `CONDA_PREFIX`
set, which is useful for scripts that call conda-aware libraries.
