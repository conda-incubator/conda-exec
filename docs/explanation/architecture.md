# Architecture

## Overview

conda-exec is a conda plugin for ephemeral package execution. It creates
cached, isolated environments and runs tools from them without modifying the
user's shell `PATH` or project environment.

In addition to the `conda exec` subcommand, conda-exec provides a
standalone `ce` command. It is a console script entry point
(`ce = "conda_exec.main:main"` in `pyproject.toml`) that creates its own
`ArgumentParser` with `prog="ce"` and calls the same `configure_parser()`
and `execute()` functions as `conda exec`.

```{tip}
The `ce` command bypasses conda's plugin loading. Use it when startup cost
or shebang portability matters.
```

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
    F --> H["<b>run.py</b><br>subprocess.run with PATH prepend<br>(or activation env vars with --activate)"]
    H --> I(["Exit code forwarded"])
```

### Script execution

When the tool argument is a path to an existing file, conda-exec switches
to script mode:

```{mermaid}
flowchart TD
    A["<b>conda exec script.py</b>"] --> B["<b>execute.py</b><br>Path(tool).is_file() → script mode"]
    B --> C["<b>script.py</b><br>Parse PEP 723 metadata block"]
    C --> D{"Matching lock data?"}
    D -- yes --> E["<b>lockfile.py</b><br>Create cached env from lock"]
    D -- no --> F{Has dependencies?}
    F -- no metadata --> G["<b>run_script_directly</b><br>Run with current Python"]
    F -- has deps --> H{Has PyPI deps?}
    H -- yes --> I{"conda-pypi available?"}
    I -- no --> J(["Error: conda-pypi required"])
    I -- yes --> K["Add conda-pypi channel"]
    H -- no --> K
    K --> L["<b>cache.py</b><br>Compute script cache key"]
    L --> M{"Cache exists?"}
    M -- hit --> N["<b>binaries.py</b><br>Find python in prefix"]
    M -- miss --> O["<b>Solver + transaction</b><br>Resolve conda + PyPI deps together"]
    O --> N
    E --> N
    N --> P["<b>run.py</b><br>Run python script.py in prefix"]
    P --> Q(["Exit code forwarded"])
```

## Why not conda run?

[conda run](https://docs.conda.io/projects/conda/en/stable/commands/run.html)
executes commands inside an existing environment. conda-exec starts from a
package spec, creates or reuses a cached environment, and then calls the
tool directly with {py:func}`subprocess.run`.

Most CLI tools do not need activation environment variables. The default
PATH-prepend path avoids shell activation and output wrapping. Users can
opt into conda activation variables with `--activate`.

## Why not extend conda-global?

conda-global manages persistent, user-facing tool installations with PATH
integration. conda-exec manages disposable cached environments for
execution. The two models should not share state or prefixes.

## Why require conda-rattler-solver?

conda-exec calls conda's cached solver backend when it creates an
environment. The project requires `conda-rattler-solver` so cold solves stay
practical for one-off commands.
