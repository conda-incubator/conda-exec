# Architecture

## Overview

conda-exec is a conda plugin that enables ephemeral package execution. It creates cached, isolated environments and runs tools from them without modifying the user's PATH or global state.

## Flow

```{mermaid}
flowchart TD
    A["<b>conda exec ruff check .</b>"] --> B["<b>plugin.py</b><br>Register exec and x subcommands"]
    B --> C["<b>cli/main.py</b><br>Parse args, dispatch to handler"]
    C --> D["<b>cli/run.py</b><br>Extract tool name, build specs list"]
    D --> E{"<b>cache.py</b><br>Compute cache key, check cache"}
    E -- cache hit --> F["<b>binaries.py</b><br>Find binary in prefix"]
    E -- cache miss --> G["<b>Solver + transaction</b><br>Create env in ~/.conda/exec/envs/"]
    G --> F
    F --> H["<b>run.py</b><br>subprocess.run with PATH prepend<br>(or full activation with --activate)"]
    H --> I(["Exit code forwarded"])
```

## Prior art

The idea of running tools from conda packages without a persistent install
has come up several times in the conda ecosystem:

### conda-execute (2015)

[conda-execute](https://github.com/conda-tools/conda-execute) by Phil Elson
allowed running Python scripts with inline dependency declarations embedded
in comments (similar to what [PEP 723](https://peps.python.org/pep-0723/)
and `uv run` do today). It created temporary environments from those inline
specs and cached them by hash. The project has been unmaintained since 2019
and its conda-forge feedstock is archived.

conda-exec solves a different problem: running packaged CLI tools (not
scripts with inline deps) from ephemeral environments, integrated as a
conda plugin with subcommands (`conda exec` / `conda x`).

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
| **conda exec** | **conda** | **`conda exec ruff check .`** |

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
| conda-exec | Ephemeral package execution |
