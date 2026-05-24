# Architecture

## Overview

conda-exec is a conda plugin that enables ephemeral package execution. It creates cached, isolated environments and runs tools from them without modifying the user's PATH or global state.

In addition to the `conda exec` subcommand, conda-exec provides a standalone `ce` command. This is a console script entry point (`ce = "conda_exec.main:main"` in pyproject.toml) that creates its own `ArgumentParser` with `prog="ce"` and calls the same `configure_parser()` and `execute()` functions as `conda exec`. The relationship mirrors how `uvx` is a standalone alias for `uv tool run`: `ce ruff check .` is equivalent to `conda exec ruff check .`, but shorter to type and usable without conda's plugin system loaded.

## Flow

### Tool execution

```{mermaid}
flowchart TD
    A["<b>conda exec ruff check .</b>"] --> B["<b>plugin.py</b><br>Register exec subcommand"]
    B --> C["<b>cli.py</b><br>Parse args, dispatch to handler"]
    C --> D["<b>execute.py</b><br>Extract tool name, build specs list"]
    D --> E{"<b>cache.py</b><br>Compute cache key, check cache"}
    E -- cache hit --> F["<b>binaries.py</b><br>Find binary in prefix"]
    E -- cache miss --> G["<b>Solver + transaction</b><br>Create env in ~/.conda/exec/envs/"]
    G --> F
    F --> H["<b>run.py</b><br>subprocess.run with PATH prepend<br>(or full activation with --activate)"]
    H --> I(["Exit code forwarded"])
```

### Script execution

When the tool argument is a path to an existing file, conda-exec switches
to script mode:

```{mermaid}
flowchart TD
    A["<b>conda exec script.py</b>"] --> B["<b>execute.py</b><br>Path(tool).is_file() → script mode"]
    B --> C["<b>script.py</b><br>Parse PEP 723 metadata block"]
    C --> D{Has dependencies?}
    D -- no metadata --> E["<b>run_script_directly</b><br>Run with current Python"]
    D -- has deps --> F{Has PyPI deps?}
    F -- yes --> G{"conda-pypi available?"}
    G -- no --> H(["Error: conda-pypi required"])
    G -- yes --> I["Add conda-pypi channel"]
    F -- no --> I
    I --> J["<b>cache.py</b><br>Compute script cache key"]
    J --> K{"Cache exists?"}
    K -- hit --> L["<b>binaries.py</b><br>Find python in prefix"]
    K -- miss --> M["<b>Solver + transaction</b><br>Resolve conda + PyPI deps together"]
    M --> L
    L --> N["<b>run.py</b><br>Run python script.py in prefix"]
    N --> O(["Exit code forwarded"])
```

## Prior art

The idea of running tools from conda packages without a persistent install
has come up several times in the conda ecosystem:

### conda-execute (2015)

[conda-execute](https://github.com/conda-tools/conda-execute) by Phil Elson
allowed running Python scripts with inline dependency declarations embedded
in YAML comments. It created temporary environments from those inline specs
and cached them by hash. The project has been unmaintained since 2019
and its conda-forge feedstock is archived.

conda-exec builds on this concept with two key differences: it supports
both packaged CLI tools (`conda exec ruff`) and scripts with inline
metadata (`conda exec script.py`), and it uses the now-standardized
[PEP 723](https://peps.python.org/pep-0723/) TOML format instead of
YAML, with a `[tool.conda]` extension for conda-native dependencies.

### conda issue #2379 (2016)

[conda/conda#2379](https://github.com/conda/conda/issues/2379) requested a
fast way to execute commands inside existing environments without the
overhead of `conda activate`. The discussion led to `conda run`, which
shipped in conda 4.6 (2018). The issue was closed in October 2025 with
`conda run` as the official solution.

conda-exec is complementary to `conda run`: while `conda run` executes
commands in environments that already exist, conda-exec creates ephemeral
cached environments on the fly from package specs. They address different
use cases.

### conda-exec shell script on conda-forge (2019)

A [minimal shell script](https://github.com/conda-forge/conda-exec-feedstock)
by Patrick Sodre that activates an existing conda environment and uses
`exec` to replace the process with a given command. It was last updated
in 2020 and has effectively zero downloads. It requires a full environment
path as input and does not create environments.

conda-exec is fundamentally different: it resolves package specs, creates
cached environments via the solver, discovers binaries, and manages the
cache lifecycle.

### Comparable tools in other ecosystems

conda-exec fills the same role as these tools in their respective ecosystems:

| Tool | Ecosystem | Example |
| ---- | --------- | ------- |
| [npx](https://docs.npmjs.com/cli/commands/npx) | Node.js | `npx prettier --write .` |
| [uvx](https://docs.astral.sh/uv/guides/tools/) | Python (uv) | `uvx ruff check .` |
| [pipx run](https://pipx.pypa.io/) | Python (pip) | `pipx run black .` |
| **conda exec** / **ce** | **conda** | **`conda exec ruff check .`** or **`ce ruff check .`** |

## PEP 723 and the `[tool.conda]` extension

[PEP 723](https://peps.python.org/pep-0723/) standardizes inline script
metadata in Python scripts using TOML in comment blocks. The standard
`dependencies` field declares PyPI packages, and `requires-python`
constrains the Python version.

conda-exec extends this with a `[tool.conda]` table for conda-native
dependencies:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19"]
# ///
```

When both PyPI and conda dependencies are declared, all packages are
resolved together in a single environment solve. PyPI packages are
resolved through the [conda-pypi](https://github.com/conda-incubator/conda-pypi)
channel, which converts PyPI wheels into conda packages so the rattler
solver can handle both in one pass.

Scripts with only `[tool.conda].dependencies` work without conda-pypi.
Scripts with only `dependencies` (PyPI) require conda-pypi to be installed.

### Forward compatibility

[PEP 725](https://peps.python.org/pep-0725/) (draft) and
[PEP 804](https://peps.python.org/pep-0804/) (draft) are working toward
a standardized way to declare non-PyPI dependencies (`[external]` table
and a cross-ecosystem dependency name registry). When those PEPs are
accepted, conda-exec can support both `[tool.conda]` and `[external]`
simultaneously.

## Why not conda run?

`conda run` uses `wrap_subprocess_call()` which generates activation shell scripts, captures output by default, and adds overhead. Most CLI tools don't need full conda activation. Direct `subprocess.run` with PATH prepended is simpler, faster, and avoids output-capture pitfalls.

## Why not extend conda-global?

conda-global manages persistent, user-facing tool installations with PATH integration via trampolines. conda-exec manages ephemeral cached environments for one-shot execution. They are two distinct models that should not share state or environment prefixes.

## Why require conda-rattler-solver?

Ephemeral execution must be fast. The rattler solver (via resolvo) is significantly faster than classic libmamba for cold solves. Since conda-express (cx) already ships conda-rattler-solver as the default, and conda-exec is designed to ship as part of that distribution, this is a natural requirement.

## Part of the conda-express ecosystem

conda-exec is one of several plugins that ship with conda-express (cx), a single-binary conda distribution:

| Plugin | Purpose |
|--------|---------|
| conda-rattler-solver | Modern solver backend |
| conda-spawn | Subshell-based activation |
| conda-self | Self-update |
| conda-workspaces | Multi-environment workspaces |
| conda-global | Persistent global tools |
| conda-completion | Shell tab completion |
| conda-pypi | PyPI interop layer |
| conda-exec | Ephemeral package execution |
