# conda-exec

Ephemeral package execution for conda. Run commands from conda packages
without installing them permanently, or run Python scripts with inline
dependency metadata.

```bash
conda exec ruff check .
conda exec script.py
```

:::{image} ../demos/quickstart.gif
:alt: conda-exec quickstart demo
:width: 100%
:::

conda-exec creates a cached, isolated environment, runs the tool or script,
and exits. The environment is reused on later runs but is not added to
`PATH` permanently. Think
[npx](https://docs.npmjs.com/cli/commands/npx) or
[uvx](https://docs.astral.sh/uv/guides/tools/), with conda packages and
channels.

## Install

::::{tab-set}

:::{tab-item} conda

```bash
conda install -c conda-forge conda-exec conda-rattler-solver
```

:::

::::

## Usage

```bash
conda exec ruff check .                            # run a tool
ce ruff check .                                    # standalone alias
conda exec "ruff>=0.4" check .                     # pin a version
conda exec --with pytest ruff check .              # add extra packages
conda exec -c bioconda samtools view file.bam      # use a different channel
conda exec script.py                               # run a script with inline deps
conda exec --lock script.py                        # record a repeatable script env
```

---

::::{grid} 2
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Getting started
:link: quickstart
:link-type: doc

Install conda-exec and run your first cached tool.
:::

:::{grid-item-card} {octicon}`mortar-board` Tutorials
:link: tutorials/index
:link-type: doc

Walk through first runs, scripts, and lock data.
:::

:::{grid-item-card} {octicon}`list-unordered` How-to guides
:link: how-to/index
:link-type: doc

Run scripts, manage cached environments, and clean up disk.
:::

:::{grid-item-card} {octicon}`tools` Run tools
:link: how-to/run-tools
:link-type: doc

Run command-line tools from conda packages without permanent installs.
:::

:::{grid-item-card} {octicon}`terminal` CLI reference
:link: reference/cli
:link-type: doc

Complete command-line documentation for `conda exec`.
:::

:::{grid-item-card} {octicon}`file-directory` Cache layout
:link: reference/cache-layout
:link-type: doc

How cached environments are structured on disk.
:::

:::{grid-item-card} {octicon}`gear` Architecture
:link: explanation/architecture
:link-type: doc

Design decisions, solver integration, and how conda-exec fits
into the conda plugin ecosystem.
:::

:::{grid-item-card} {octicon}`gear` Ecosystem fit
:link: explanation/ecosystem-fit
:link-type: doc

When to use conda-exec instead of named environments, `conda run`, or
project managers.
:::

::::

```{toctree}
:hidden:
:caption: Getting started

quickstart
```

```{toctree}
:hidden:
:caption: Tutorials

First run <tutorials/first-run>
Run a script <tutorials/run-script>
Share a locked script <tutorials/share-locked-script>
```

```{toctree}
:hidden:
:caption: How-to guides

Run scripts <how-to/run-scripts>
Run tools <how-to/run-tools>
Use PyPI dependencies <how-to/use-pypi-dependencies>
Lock scripts <how-to/lock-scripts>
Manage cache <how-to/manage-cache>
Configure cleanup <how-to/configure-cleanup>
Use channels <how-to/use-channels>
Use activation <how-to/use-activation>
Pin versions <how-to/version-constraints>
Use in CI/CD <how-to/ci-cd>
Troubleshooting <how-to/troubleshooting>
```

```{toctree}
:hidden:
:caption: Reference

CLI <reference/cli>
Package specs <reference/package-specs>
Cache layout <reference/cache-layout>
Environment variables <reference/environment-variables>
Cache list JSON <reference/list-json>
Error messages <reference/errors>
Script metadata <reference/script-metadata>
Script locks <reference/script-locks>
```

```{toctree}
:hidden:
:caption: Explanation

Architecture <explanation/architecture>
Ecosystem fit <explanation/ecosystem-fit>
Dependency resolution <explanation/dependency-resolution>
Caching <explanation/caching>
Script locks <explanation/script-locks>
Security <explanation/security>
Prior art <explanation/prior-art>
```
