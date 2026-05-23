# conda-exec

Ephemeral package execution for conda. Run any conda package without installing it permanently.

```bash
conda exec ruff check .
conda x ruff check .
```

conda-exec creates a cached, isolated environment for the tool, runs it, and exits.
The environment is cached for fast re-use but is not on PATH and is fully disposable.

## Install

::::{tab-set}

:::{tab-item} conda

```bash
conda install -c conda-forge conda-exec
```

:::

:::{tab-item} cx

Already included when using
[conda-express (cx)](https://github.com/conda-incubator/conda-express).

:::

::::

## Usage

```bash
conda exec ruff check .                            # run ruff
conda x ruff check .                               # short alias
conda exec --spec "ruff>=0.4" ruff check .          # pin a version
conda exec --with pytest ruff check .               # add extra packages
conda exec -c bioconda samtools view file.bam       # use a different channel
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

Manage cached environments, force refresh, clean up disk.
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

tutorials/index
```

```{toctree}
:hidden:
:caption: How-to guides

how-to/index
```

```{toctree}
:hidden:
:caption: Reference

reference/index
```

```{toctree}
:hidden:
:caption: Explanation

explanation/index
```
