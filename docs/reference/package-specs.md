# Package specs

conda-exec accepts conda match specs anywhere it asks for a package:

- the positional `TOOL`
- each `--with MATCHSPEC`
- `[tool.conda].dependencies` in script metadata

The strings are parsed with conda's
{py:class}`~conda.models.match_spec.MatchSpec` model and passed to the
solver. For the full grammar, see conda's
[package specification](https://docs.conda.io/projects/conda/en/stable/user-guide/concepts/pkg-specs.html)
documentation.

## Tool specs

The `TOOL` argument identifies both what package to install and what
executable to run:

```bash
conda exec ruff check .
conda exec "ruff>=0.4,<0.5" check .
```

conda-exec extracts the package name from the match spec and uses that name
as the binary name. For `ruff>=0.4,<0.5`, the package name and executable
name are both `ruff`.

## Common match spec forms

| Form | Example | Meaning |
| ---- | ------- | ------- |
| Name | `ruff` | Install any available `ruff` |
| Version range | `ruff>=0.4,<0.5` | Install a version in the range |
| Exact version | `ruff==0.4.3` | Install exactly that version |
| Build string | `zlib=1.2.13=h5eee18b_5` | Match version and build |
| Channel-qualified | `conda-forge::ruff` | Require the package from a channel |

Quote match specs in shells whenever they contain `<`, `>`, `=`, `!`, `*`,
spaces, or commas:

```bash
conda exec "ruff>=0.4,<0.5" check .
conda exec --with "python=3.12" jupyter lab
```

## Extra specs with --with

`--with` adds packages to the same ephemeral environment as the tool:

```bash
conda exec --with pytest --with hypothesis ruff check tests/
```

Each value is parsed as a match spec. Extras are not executed directly;
they are installed so the tool can import or call them.

This is useful when:

- a tool imports optional plugins
- a command needs a particular Python version
- you want a tiny throwaway environment for a Python one-liner

Example:

```bash
conda exec --with pandas --with pyarrow python -- -c "import pandas, pyarrow"
```

## Script dependency specs

Conda dependencies in scripts also use match specs:

```python
# /// script
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["numpy>=2", "pandas", "python-dateutil"]
# ///
```

Top-level PEP 723 `dependencies` are different: they are PyPI
[requirement specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/)
and require `conda-pypi`.

## Channel behavior

Tool mode defaults to `conda-forge` when no channel is provided:

```bash
conda exec ruff check .
```

As soon as you pass one or more `-c/--channel` flags, conda-exec uses the
provided channel list:

```bash
conda exec -c conda-forge -c bioconda samtools view input.bam
```

Script mode uses channels from `[tool.conda].channels`, then appends any
CLI `--channel` values. If the combined list is empty, it defaults to
`conda-forge`.

Channel order is passed to conda's solver. Conda's configured
[channel priority](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-channels.html#strict-channel-priority)
policy still applies.

## Cache identity

The cache key includes the normalized spec list and channel list. These
commands create distinct cached environments:

```bash
conda exec ruff check .
conda exec "ruff>=0.4" check .
conda exec --with pytest ruff check .
conda exec -c defaults ruff check .
```

Spec order does not matter for cache identity because specs are normalized
and sorted before hashing. Channel order matters to the solver, but the
cache key uses the sorted channel list so the same set of channels maps to
the same cache entry.

## Package name and executable name

Tool mode expects the executable name to match the parsed package name.
There is no separate flag for "install package X but run executable Y".

If the package name and executable differ, use a script, a named conda
environment, or the package that matches the command you want to run.

When the environment is solved but no matching executable exists,
conda-exec raises `BinaryNotFoundError`.

## Invalid specs

Invalid match specs fail before any environment is created:

```text
conda exec: invalid match spec for tool '<spec>': <detail>
```

Fix the spec syntax, quote shell-sensitive characters, or move complex
requirements into a script metadata block where TOML quoting is clearer.
