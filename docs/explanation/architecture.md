# Architecture

## Overview

conda-exec is a conda plugin that enables ephemeral package execution. It creates cached, isolated environments and runs tools from them without modifying the user's PATH or global state.

In addition to the `conda exec` subcommand, conda-exec provides a standalone `ce` command. This is a console script entry point (`ce = "conda_exec.main:main"` in pyproject.toml) that creates its own `ArgumentParser` with `prog="ce"` and calls the same `configure_parser()` and `execute()` functions as `conda exec`. The relationship mirrors how `uvx` is a standalone alias for `uv tool run`: `ce ruff check .` is equivalent to `conda exec ruff check .`, but shorter to type and usable without conda's plugin system loaded.

```{tip}
The `ce` command bypasses conda's plugin loading, so it starts faster than
`conda exec`. If you use conda-exec frequently, `ce` is the recommended
entry point.
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

## Why not conda run?

`conda run` uses `wrap_subprocess_call()` which generates activation shell scripts, captures output by default, and adds overhead. Most CLI tools don't need activation environment variables. Direct `subprocess.run` with PATH prepended is simpler, faster, and avoids output-capture pitfalls.

## Why not extend conda-global?

conda-global manages persistent, user-facing tool installations with PATH integration via trampolines. conda-exec manages ephemeral cached environments for one-shot execution. They are two distinct models that should not share state or environment prefixes.

## Why require conda-rattler-solver?

Ephemeral execution must be fast. The rattler solver (via resolvo) is significantly faster than classic libmamba for cold solves, so conda-exec requires `conda-rattler-solver` for cached environment creation.
