# Run command-line tools

Use tool mode when you want a command from a conda package for one job,
without installing that package into `base`, your project environment, or
your shell `PATH`.

## Run a package

Run the package name followed by the command arguments:

```bash
conda exec ruff check .
```

conda-exec creates or reuses a cached environment, finds `ruff` inside that
environment, and runs it with the remaining arguments. The tool's stdout,
stderr, and exit code are forwarded directly.

The standalone `ce` command uses the same parser and execution path:

```bash
ce ruff check .
```

Use `ce` for frequent interactive use and for shebangs. Use `conda exec`
when you want the command to read naturally as a conda subcommand.

## Pass tool options safely

Arguments after the tool name are passed to the tool:

```bash
conda exec ruff check --select F401 src/
```

If the tool arguments begin with dashes or could be confused with
conda-exec options, add `--` after the tool name:

```bash
conda exec ruff -- --config pyproject.toml check .
```

The separator is stripped before the tool runs. The tool receives
`--config pyproject.toml check .`.

## Pin the tool version

Put a conda match spec in the tool position:

```bash
conda exec "ruff>=0.4,<0.5" check .
```

Quote specs that contain `<`, `>`, `=`, `!`, or spaces so your shell does
not treat them as redirection or control characters.

The executable name comes from the package name parsed out of the match
spec. In the example above, conda-exec installs a package matching
`ruff>=0.4,<0.5` and looks for an executable named `ruff`.

## Add packages to the tool environment

Use `--with` for packages the tool should have available at runtime:

```bash
conda exec --with pytest ruff check tests/
conda exec --with "python=3.12" jupyter lab
conda exec --with pandas --with pyarrow python -- -c "import pandas"
```

Every `--with` value is a conda match spec. Extras become part of the cache
key, so a plain `ruff` environment and a `ruff` plus `pytest` environment
are cached separately.

:::{image} ../../demos/extra-packages.gif
:alt: Demo showing conda exec with --with and the -- argument separator
:width: 100%
:::

## Use another channel

By default, conda-exec searches `conda-forge`.

Use `-c` or `--channel` to provide channels explicitly:

```bash
conda exec -c conda-forge -c bioconda samtools view input.bam
```

When you pass any `-c` flag, conda-exec uses the channels you gave. Include
`conda-forge` yourself when a domain channel such as `bioconda` depends on
it.

## Handle package names and executable names

Tool mode assumes the package name and executable name match. This is the
normal conda UX for command packages such as `ruff`, `samtools`, `jq`,
`prettier`, and `shellcheck`.

If a package installs an executable with a different name, conda-exec does
not currently have a separate "install this package, run that binary" flag.
Use one of these patterns instead:

- Find the conda package whose name matches the executable.
- Use a script with inline metadata and call the desired executable from
  Python.
- Create a named environment and use
  [conda run](https://docs.conda.io/projects/conda/en/stable/commands/run.html)
  when the package layout is unusual or needs custom activation behavior.

If conda-exec creates the environment but cannot find the expected binary,
it reports `binary '<name>' not found in cached environment`.

## Refresh one tool cache

Use `--refresh` when you want to discard the cached environment for exactly
the requested spec and solve again:

```bash
conda exec --refresh ruff check .
```

Other cached versions or channel combinations for the same tool are left
alone.

## Use activation variables

Most command-line tools only need their environment's binary directory on
`PATH`, which is the default. If a tool checks `CONDA_PREFIX` or other
activation variables, add `--activate`:

```bash
conda exec --activate -c conda-forge -c bioconda snakemake --cores 4
```

Activation mode asks conda's activator for environment variables. It does
not run `activate.d` shell scripts. If a package depends on activation
scripts, use a named conda environment and
[conda run](https://docs.conda.io/projects/conda/en/stable/commands/run.html).

## Common command patterns

Run project checks without adding tools to the project environment:

```bash
conda exec ruff check .
conda exec ruff format --check .
conda exec mypy src/
```

Run a one-off data or shell utility:

```bash
conda exec jq '.name' package.json
conda exec yq '.channels[]' environment.yml
```

Run a domain tool from an additional channel:

```bash
conda exec -c conda-forge -c bioconda samtools flagstat reads.bam
```

Try a newer tool without changing any existing environment:

```bash
conda exec "ruff>=0.5" check .
```

See [Package specs](../reference/package-specs.md) for the exact match spec
and cache-key rules.
