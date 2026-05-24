# conda-exec

Ephemeral package execution for conda. Run any conda package without installing it permanently, or run Python scripts with inline dependency metadata.

```bash
conda exec ruff check .
conda exec script.py
```

conda-exec creates a cached, isolated environment, runs the tool or script, and exits.
The environment is cached for fast re-use but is not on PATH and is fully disposable.
Think [npx](https://docs.npmjs.com/cli/commands/npx) or
[uvx](https://docs.astral.sh/uv/guides/tools/) for the conda ecosystem.

## Install

::::{tab-set}

:::{tab-item} conda

```bash
conda install -c conda-forge conda-exec
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
```

---

::::{grid} 2
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Getting started
:link: quickstart
:link-type: doc

Install and run your first tool in under a minute.
:::

:::{grid-item-card} {octicon}`mortar-board` Tutorials
:link: tutorials/index
:link-type: doc

Walk through first runs, caching, and advanced specs.
:::

:::{grid-item-card} {octicon}`list-unordered` How-to guides
:link: how-to/index
:link-type: doc

Run scripts, manage cached environments, and clean up disk.
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
```

```{toctree}
:hidden:
:caption: How-to guides

Run scripts <how-to/run-scripts>
Manage cache <how-to/manage-cache>
```

```{toctree}
:hidden:
:caption: Reference

CLI <reference/cli>
Cache layout <reference/cache-layout>
```

```{toctree}
:hidden:
:caption: Explanation

Architecture <explanation/architecture>
```
