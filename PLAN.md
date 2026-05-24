# Plan: conda-exec -- ephemeral package execution for conda

## Context

The conda ecosystem is gaining a curated set of plugins that, together with conda-express (cx), form a modern conda distribution. cx is a single-binary Rust bootstrapper that installs conda with conda-rattler-solver as the default solver, then hands off to the installed conda binary transparently. The vision: cx eventually becomes the canonical `conda` distribution, shipping these plugins out of the box:

| Plugin | Purpose | Status |
|--------|---------|--------|
| conda-rattler-solver | Modern solver backend (resolvo) | Shipping with cx |
| conda-spawn | Subshell-based activation (`conda spawn`) | Shipping with cx |
| conda-self | Self-update for conda itself | In progress |
| conda-workspaces | Multi-environment project workspaces | Released (0.5.x) |
| conda-global | Persistent global CLI tools (like pipx) | Released (alpha) |
| conda-completion | Shell tab completion (Python + Rust hybrid) | Released (0.2.x) |
| conda-pypi | PyPI interop layer | In progress |
| **conda-exec** | **Ephemeral package execution (like npx/uvx)** | **This plan** |

conda-exec fills the last major gap: running a tool from a conda package without installing it permanently. `conda exec ruff check .` creates a cached ephemeral environment, runs the command, and exits. The environment is cached for fast re-use but is not on PATH and is fully disposable.

This is the conda equivalent of `npx` (Node), `uvx` (Python/uv), or `pipx run`. It addresses conda/conda#13538 (`conda run -x` proposal by @jaimergp).

### Why not extend conda-global?

conda-global manages persistent, user-facing tool installations with PATH integration via trampolines. conda-exec manages ephemeral, cached environments for one-shot execution. They are two distinct models:

- **conda-global**: persistent environments, trampoline binaries on PATH, manifest tracking, user explicitly installs/removes tools
- **conda-exec**: ephemeral cached environments, no PATH modification, automatic cache management, user just runs a command

They share some implementation patterns (solver invocation, binary discovery) but should not share state or environment prefixes.

### Why require conda-rattler-solver?

Ephemeral execution must be fast. The rattler solver (via resolvo) is significantly faster than classic libmamba for cold solves. Since cx already ships conda-rattler-solver as the default, and conda-exec is designed to ship as part of the cx distribution, this is a natural requirement. conda-exec will check for the solver at startup and provide a clear error if it's missing.

## Path layout

```
~/.conda/exec/                       # CONDA_EXEC_HOME override
  envs/
    ruff--a3f8b2c1d9e0f4a7/          # cached env for `conda exec ruff`
      conda-meta/
      bin/ruff
    samtools--7e2d9f04b1c3e8/        # cached env for `conda exec samtools`
      conda-meta/
      bin/samtools
```

Primary path is `~/.conda/exec/`. On Windows, falls back to `platformdirs.user_data_dir("conda", "conda") / "exec"` if `~/.conda/exec/` does not exist. The `CONDA_EXEC_HOME` environment variable overrides both for testing and custom layouts.

Cache keys are always `{tool}--{hash16}` where the hash is derived from sorted, normalized specs and channels. This means different specs for the same tool get separate cached environments.

This is deliberately separate from conda-global's `~/.conda/global/` tree.

## Architecture

```
conda exec ruff check .
    |
    v
plugin.py              Register "exec" subcommand; main.py provides standalone "ce" command
    |
    v
cli.py                 Parse args, dispatch to --list / --clean / run mode
    |
    v
execute.py             Resolve specs, compute cache key, create/reuse env
    |
    v
cache.py               CacheManager: get_or_create, create (solver + transaction),
    |                     exists, remove, list_cached, cache_key, touch
    |
    +--[cache hit]------> touch history mtime, find_binary() in cached prefix
    |
    +--[cache miss]-----> solver + transaction (via conda APIs)
    |                       atomic tmp dir + rename to envs/{tool}--{hash}/
    |
    v
run.py                 run_in_prefix(): subprocess.run with PATH prepend
    |                     or full activation (build_activated_env) if --activate
    v
exit code              forwarded from subprocess
```

### Why direct subprocess.run instead of conda run?

`conda run` uses `wrap_subprocess_call()` which generates activation shell scripts, captures output by default, and adds overhead. Most CLI tools (ruff, samtools, jq, ripgrep) don't need full conda activation -- they just need to be executed from their prefix. Direct `subprocess.run` with `PATH` prepended to include the prefix's `bin/` directory is simpler, faster, and avoids the output-capture pitfalls of `conda run`.

For tools that DO need activation (e.g., those depending on `CONDA_PREFIX` environment variables), the `--activate` flag triggers full conda activation via `build_activated_env()` in `run.py`.

## Module layout (current)

All modules live at the package root. No subpackages.

```
conda_exec/
  __init__.py          Package init
  _version.py          Auto-generated version (hatch-vcs)
  plugin.py            Plugin registration: yields "exec" CondaSubcommand
  main.py              Standalone "ce" console script entry point
  cli.py               Argument parser (configure_parser) and dispatch (execute)
  execute.py           Run-mode handler: resolves specs, manages cache, invokes tool
  cache.py             CacheManager class + CacheEntry dataclass + cache key hashing
  binaries.py          Binary discovery: find_binary, discover_binaries, symlink safety
  run.py               Subprocess execution: PATH-prepend or full activation mode
  paths.py             Filesystem layout: data_dir(), envs_dir(), CONDA_EXEC_HOME
  exceptions.py        CondaExecError, SolveError, BinaryNotFoundError, SolverNotAvailableError
  list.py              --list handler: table and JSON output of cached environments
  clean.py             --clean handler: age-based cleanup with confirmation prompts
  format.py            Display utilities: format_size(), format_age()
  script.py            PEP 723 inline metadata parser and ScriptMetadata dataclass
  pypi.py              Optional conda-pypi availability check
```

## Implementation

### Phase 1: MVP -- single package execution (DONE)

Goal: `conda exec ruff check .` works end-to-end. Also available as standalone `ce ruff check .`.

#### 1.1 Project scaffolding

Created the conda-exec repository:

- `pyproject.toml` -- hatchling + hatch-vcs build, `conda >=25.1` + `platformdirs >=4.0` deps, entry point `[project.entry-points.conda] "conda-exec" = "conda_exec.plugin"`
- `conda_exec/__init__.py`
- `conda_exec/plugin.py` -- register subcommands
- `conda_exec/exceptions.py` -- `SolveError`, `BinaryNotFoundError`, `SolverNotAvailableError`
- `AGENTS.md` -- coding conventions

#### 1.2 Plugin registration (`conda_exec/plugin.py`) and standalone entry point (`conda_exec/main.py`)

Registers `exec` as a conda subcommand. Lazily imports `configure_parser` and `execute` from `.cli` inside the hook to keep plugin load under 1ms. A standalone `ce` command is provided via `[project.scripts]` in `pyproject.toml`, using `conda_exec.main:main` as the entry point. Both share the same CLI handler.

```python
@hookimpl
def conda_subcommands() -> Iterable[CondaSubcommand]:
    from conda.plugins.types import CondaSubcommand
    from .cli import configure_parser, execute

    yield CondaSubcommand(
        name="exec",
        summary="Run a command from a conda package without installing it.",
        action=execute,
        configure_parser=configure_parser,
    )
```

#### 1.3 Path helpers (`conda_exec/paths.py`)

Uses `~/.conda/exec/` as the primary path on all platforms, with `platformdirs.user_data_dir` as a Windows-only fallback. `CONDA_EXEC_HOME` env var overrides everything. Both functions are `@lru_cache(maxsize=1)` for performance.

#### 1.4 Cache manager (`conda_exec/cache.py`)

`CacheManager` with these methods:

- `__init__(envs_dir=None)` -- defaults to `paths.envs_dir()`
- `get_or_create(key, specs, channels) -> tuple[Path, bool]` -- returns cached prefix and whether it was newly created
- `create(key, specs, channels) -> Path` -- solver + transaction with atomic tmp dir + rename
- `exists(key) -> bool` -- fast stat-only check (dir + conda-meta exists)
- `remove(key)` -- `unregister_env()` + `rm_rf()`
- `list_cached() -> list[CacheEntry]` -- enumerates envs with PrefixData metadata
- `cache_key(tool, specs, channels) -> str` -- `{tool}--{sha256hex[:16]}` from sorted normalized specs+channels
- `prefix_for(key) -> Path` -- validates key format, length, and path traversal safety
- `touch(prefix)` -- updates `conda-meta/history` mtime for staleness tracking (debounces within 1 hour)
- `script_cache_key(metadata) -> str` -- deterministic `script--{hash16}` from all dependency information

`CacheEntry` is a frozen dataclass with: `key`, `tool`, `prefix`, `created`, `last_modified`, `size`, `package_count`.

Security: `SAFE_TOOL_RE` and `SAFE_KEY_RE` validate names. `prefix_for()` checks `is_relative_to()` to prevent path traversal. Max key length is 200 chars.

Solver: uses `context.plugin_manager.get_cached_solver_backend()`, raises `SolverNotAvailableError` if None.

#### 1.5 Binary discovery (`conda_exec/binaries.py`)

Functions:

- `find_binary(prefix, name) -> Path | None` -- looks in `BIN_DIRECTORY`, tries `.exe`/`.bat`/`.cmd` on Windows, validates with `is_within_prefix()` for symlink safety
- `discover_binaries(prefix) -> list[str]` -- lists all executables in prefix's bin dir
- `is_executable(path) -> bool` -- checks Unix permission bits
- `is_within_prefix(path, prefix) -> bool` -- resolves symlinks and checks `is_relative_to()`

Uses `conda.common.path.BIN_DIRECTORY` and `conda.common.compat.on_win` for cross-platform correctness.

#### 1.6 CLI parser and dispatch (`conda_exec/cli.py`)

Single flat module (no `cli/` subpackage). `configure_parser()` sets up:

- Mutually exclusive `--list` / `--clean` mode flags
- `-c/--channel` (repeatable), `--with` (repeatable), `--activate`, `--refresh`
- `--json` (for --list), `--all`, `--older-than`, `--dry-run`, `-y/--yes` (for --clean)
- `TOOL` (optional positional, accepts bare names or full match specs like `ruff>=0.4`)
- `TOOL_ARGS` via `argparse.REMAINDER`

`execute()` dispatches to `list.execute_list`, `clean.execute_clean`, or `execute.execute_run` based on mode flags, using lazy imports.

#### 1.7 Run handler (`conda_exec/execute.py`)

`execute_run()` handles the main execution path:

- Parses TOOL as a `MatchSpec` to extract the package name
- Combines TOOL spec with `--with` specs
- Strips leading `--` from tool args
- Computes cache key, checks/creates environment via `CacheManager`
- Shows progress ("Creating environment for {name}... done (Xs)") on cache miss
- Finds binary via `find_binary()`, runs via `run_in_prefix()`
- Catches `CondaExecError` and prints error message + hints

#### 1.8 Subprocess execution (`conda_exec/run.py`)

- `run_in_prefix(prefix, binary, args, *, activate=False) -> int` -- default mode prepends prefix's bin dir to PATH; `--activate` mode uses `build_activated_env()` for full conda activation
- `build_activated_env(prefix) -> dict` -- uses `PosixActivator` (or `CmdExeActivator` on Windows), applies `export_vars` and `unset_vars` from `build_activate()`
- Handles `FileNotFoundError` (exit 127) and `PermissionError` (exit 126)
- Passes through stdin/stdout/stderr directly (no capture)

#### 1.9 Tests

- `tests/test_paths.py` -- verify `CONDA_EXEC_HOME` override, default path
- `tests/test_cache.py` -- cache key hashing, create/exists/remove lifecycle, security validations
- `tests/test_binaries.py` -- binary discovery in a fake prefix, symlink safety
- `tests/test_cli.py` -- argument parsing, `--` separator, `--list`/`--clean` mutual exclusion
- `tests/test_run.py` -- subprocess execution, PATH prepend, activation mode
- `tests/test_plugin.py` -- both `exec` and `x` subcommands registered
- `tests/test_exceptions.py` -- exception messages and hints
- `tests/test_integration.py` -- end-to-end tests (marked slow, require network)

### Phase 2: Cache management (DONE)

Goal: `conda exec --list` and `conda exec --clean` work.

Originally designed as `conda exec list` / `conda exec clean` subcommands, later refactored to `--list` / `--clean` flags on the main command (mutually exclusive group in argparse). This avoids the complexity of sub-subcommands and keeps the namespace clean for Phase 5's script file detection.

#### 2.1 List handler (`conda_exec/list.py`)

`execute_list(args)` displays cached environments. Table output shows Tool, Size, Last used, Packages columns with dynamic column width. `--json` outputs a JSON array with tool, key, prefix, created, last_used, size_bytes, packages fields.

#### 2.2 Clean handler (`conda_exec/clean.py`)

`execute_clean(args)` removes cached environments. Filters by: `--all` (everything), tool name (positional), or age (`--older-than DAYS`, default 30). Supports `--dry-run` (also respects `context.dry_run`), `-y/--yes` (skip confirmation). Uses `conda.reporters.confirm_yn()` for prompts.

#### 2.3 Last-used tracking

Uses `conda-meta/history` file mtime via `CacheManager.touch()` (`Path.touch()`). The `list_cached()` method reads timestamps via `PrefixData.last_modified`. No separate `.last_used` file needed -- conda's own metadata infrastructure handles it. Touch is debounced to skip updates within the last hour.

#### 2.4 Display formatting (`conda_exec/format.py`)

- `format_size(bytes)` -- human-readable sizes (B, KB, MB, GB, TB)
- `format_age(datetime)` -- relative time strings ("just now", "2 hours ago", "5 days ago")

### Phase 3: Advanced specs and extra packages (DONE)

Goal: `conda exec "ruff>=0.4" check .` and `conda exec --with pytest ruff check .`

#### 3.1 Match spec as TOOL argument

Instead of a separate `--spec` flag, the TOOL positional argument itself accepts full conda match specs. `MatchSpec(tool).name` extracts the package name for binary discovery. Examples:

```
conda exec ruff check .                    # bare name
conda exec "ruff>=0.4,<0.5" check .       # version-constrained
```

#### 3.2 `--with` flag

Repeatable flag for extra packages. Combined with the TOOL spec into the solver's spec list. Does not affect binary discovery.

#### 3.3 Cache key hashing

Implemented directly in `CacheManager.cache_key()` (no separate `specs.py` module). Normalizes all specs via `MatchSpec(s)`, sorts them, combines with sorted channels, and produces `{tool}--{sha256[:16]}`. Different specs for the same tool produce different cache keys and separate environments.

#### 3.4 `--python` flag

Not implemented. Users can achieve the same with `--with "python=3.12"`.

### Phase 4: Activation support and polish (DONE)

Goal: `conda exec --activate samtools view file.bam`

#### 4.1 `--activate` flag

Implemented in `run.py` via `build_activated_env()`. Uses `PosixActivator`/`CmdExeActivator` from `conda.activate`, applies `export_vars`/`unset_vars` to the subprocess environment. No separate `activate.py` module -- the logic is small enough to live in `run.py`.

#### 4.2 Progress display

Implemented in `execute.py`. Shows "Creating environment for {name}..." on stderr during cache miss, with elapsed time on completion. Only prints when creating (not on cache hits).

#### 4.3 conda-completion integration

Not yet implemented. Requires conda-completion 0.2.x with `completion_type` field.

### Phase 5: Inline script execution with PEP 723 (DONE)

Goal: `conda exec script.py` detects a file path in the TOOL argument, parses inline dependency metadata from the script, creates a cached environment with both conda and PyPI packages, and runs it.

#### 5.1 Background and prior art

**PEP 723** (Accepted) standardizes inline script metadata in Python scripts using TOML in comment blocks:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests<3",
#   "rich",
# ]
# ///
```

`uv run script.py` already implements this for PyPI packages. The format supports `[tool.*]` tables for tool-specific extensions.

**conda-execute** (pelson, 2015-2017) pioneered this concept for conda using YAML in comments:

```python
# conda execute
# env:
#  - python >=3
#  - numpy
# run_with: python
```

Environments were SHA-256 hashed by the metadata block and garbage-collected. The project is abandoned but proved the concept works.

**PEP 725** (Draft, active) adds `[external]` dependencies to `pyproject.toml` for non-PyPI packages (system libraries, compilers). The build/host/runtime split mirrors conda-build's metadata model. Co-authored by Jaime Rodriguez-Guerra (conda team) and Ralf Gommers.

**PEP 804** (Draft, active) defines a central registry of canonical dependency identifiers (DepURLs like `dep:generic/zlib`) and per-ecosystem mapping files that translate them to package names (`zlib` -> conda-forge's `zlib-ng`). Conda-forge is a primary test ecosystem. Also co-authored by Jaime and Michael Sarahan.

Neither PEP 725 nor 804 extends PEP 723's inline script format yet. That gap is the opportunity for conda-exec.

**conda-pypi** (0.8.x, early beta) can resolve PyPI dependencies, convert wheels to `.conda` format, and install them natively into conda environments. This enables mixed conda+PyPI resolution in a single environment.

#### 5.2 Script metadata format

Support PEP 723's standard `dependencies` field for PyPI packages, plus a `[tool.conda]` extension for conda-native packages:

```python
#!/usr/bin/env conda exec run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests>=2.31",
#   "rich",
# ]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = [
#   "samtools>=1.19",
#   "python=3.12",
# ]
# ///

import subprocess
import requests
from rich import print

result = subprocess.run(["samtools", "--version"], capture_output=True, text=True)
print(result.stdout)
```

The `[tool.conda]` table supports:
- `channels` -- list of conda channels (default: `["conda-forge"]`)
- `dependencies` -- list of conda match specs

When both `dependencies` (PyPI) and `[tool.conda].dependencies` exist, conda packages are resolved first, then PyPI packages are installed via conda-pypi into the same environment.

Scripts with only `[tool.conda].dependencies` and no top-level `dependencies` need only conda, not conda-pypi.

#### 5.3 Script detection

No subcommand needed. The positional TOOL argument checks if it resolves to an existing file:

```python
if Path(tool).is_file():
    # script mode: parse PEP 723, build env, run with python
else:
    # package mode: current behavior
```

This is the same heuristic `uv run` uses. The `--list`/`--clean` flag conversion (already shipped) cleared the namespace for this.

#### 5.4 Script metadata parser (`conda_exec/script.py`)

Implemented. Parses the `# /// script` block per PEP 723's specification.

`parse_script_metadata(path_or_text)` accepts a file path or script text directly. Returns a frozen `ScriptMetadata` dataclass with `requires_python`, `pypi_dependencies`, `conda_dependencies`, `conda_channels` (all tuples for immutability).

`extract_script_block(source)` accepts a string or any iterable of lines (e.g., an open file object) for lazy reading of large files. Warns on unclosed blocks.

TOML parsing uses `tomllib` (stdlib 3.11+) with `tomli` fallback for Python 3.10.

Safety: files larger than `MAX_SCRIPT_SIZE` (10 MB) are skipped without parsing.

#### 5.5 Cache key for scripts

The cache key incorporates all dependency information:

```python
def script_cache_key(metadata: ScriptMetadata) -> str:
    """Compute a deterministic cache key from script metadata."""
```

Hash inputs: sorted conda deps + sorted PyPI deps + sorted channels + requires-python. The key format is `script--{hash16}` to distinguish from tool-based cache keys.

#### 5.6 Script execution handler

The handler in `execute.py`:
1. Reads and parses the script's metadata block
2. Validates `requires-python` against the resolved Python version
3. Computes the cache key from metadata
4. Creates or reuses the cached environment:
   - Resolves conda dependencies via the solver
   - If PyPI dependencies exist, checks that conda-pypi is available
   - Installs PyPI packages via conda-pypi into the same prefix
5. Runs the script with `python` from the cached environment

Error cases:
- No metadata block: run with the current Python (no environment creation)
- conda-pypi not available but PyPI deps declared: clear error with install instructions
- `requires-python` mismatch: clear error showing available vs required version

#### 5.7 Shebang support

Scripts with `#!/usr/bin/env conda exec run` can be executed directly:

```bash
chmod +x script.py
./script.py
```

Note: On Linux, `env` splits the shebang differently than macOS. Testing is needed to determine whether a wrapper script is more portable than relying on `env` argument splitting.

#### 5.8 PyPI dependency installation via conda-pypi

When a script declares top-level `dependencies` (PyPI packages):

1. Check if conda-pypi is available (`import conda_pypi`)
2. After creating the conda environment, run conda-pypi's installation pipeline:
   - `dry_run_pip_json()` to resolve PyPI deps
   - Convert wheels to `.conda` format
   - Install into the prefix
3. If conda-pypi is not available, raise `PyPIDependencyError` with install instructions

The conda-pypi integration is optional. Scripts that only use `[tool.conda].dependencies` work without it.

#### 5.9 Forward compatibility with PEP 725 / PEP 804

When PEP 725 and PEP 804 are accepted and tooling matures:

- Support an `[external]` table in the inline metadata block (mirroring PEP 725's `pyproject.toml` format)
- Resolve DepURLs (e.g., `dep:generic/samtools`) to conda package names via the PEP 804 registry
- This makes scripts portable across package managers: the same `[external].dependencies` can be resolved by conda, apt, or homebrew

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
#
# [external]
# dependencies = [
#   "dep:generic/samtools>=1.19",
#   "dep:generic/htslib",
# ]
# ///
```

This is a future extension. The `[tool.conda]` approach works today and does not conflict with eventual PEP 725/804 support. When those PEPs land, conda-exec can support both simultaneously.

#### 5.10 Files (all implemented)

- `conda_exec/script.py` -- PEP 723 metadata parser and `ScriptMetadata` dataclass
- `conda_exec/pypi.py` -- conda-pypi integration (optional dependency check)
- `conda_exec/exceptions.py` -- `PyPIDependencyError`, `PythonVersionError` added
- `conda_exec/execute.py` -- script detection via `is_script_path()`, `execute_script()` handler
- `conda_exec/cache.py` -- `script_cache_key()` method on CacheManager
- `tests/test_script.py` -- metadata parser tests, script execution tests (combined into single file)

## cx distribution integration

When cx becomes the canonical conda distribution, conda-exec ships as a built-in plugin. The user experience:

```bash
# Install cx (single binary)
curl -fsSL https://get.conda.dev | sh

# cx bootstraps conda with all plugins
cx bootstrap

# These all work out of the box:
conda exec ruff check .          # ephemeral execution
ce ruff check .                  # standalone alias
conda global install gh          # persistent global tool
conda workspace install          # multi-env workspace
conda completion generate        # shell completions
conda self update                # self-update
conda spawn                      # subshell activation
```

The `cx.lock` lockfile compiled into the cx binary will include conda-exec alongside the other plugins. No separate installation step needed.

## Key files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project config, deps, entry points |
| `conda_exec/__init__.py` | Package init |
| `conda_exec/_version.py` | Auto-generated version (hatch-vcs) |
| `conda_exec/plugin.py` | Plugin registration: `exec` subcommand |
| `conda_exec/main.py` | Standalone `ce` console script entry point |
| `conda_exec/cli.py` | Argument parser and dispatch (--list / --clean / run) |
| `conda_exec/execute.py` | Run-mode handler: spec resolution, cache management, tool invocation |
| `conda_exec/cache.py` | CacheManager, CacheEntry, cache key hashing, security validation |
| `conda_exec/binaries.py` | Binary discovery with symlink safety |
| `conda_exec/run.py` | Subprocess execution: PATH-prepend or full conda activation |
| `conda_exec/paths.py` | Filesystem layout, CONDA_EXEC_HOME override |
| `conda_exec/exceptions.py` | CondaExecError hierarchy |
| `conda_exec/list.py` | --list handler: table and JSON output |
| `conda_exec/clean.py` | --clean handler: age-based cleanup with confirmation |
| `conda_exec/format.py` | Display utilities: format_size, format_age |
| `conda_exec/script.py` | (Phase 5) PEP 723 metadata parser |
| `conda_exec/pypi.py` | (Phase 5) conda-pypi integration for PyPI deps |

## Reference implementations to reuse

| Pattern | Source | How to reuse |
|---------|--------|--------------|
| Solver invocation | `conda_global/envs.py:37-77` | Copy pattern: MatchSpec, Channel, solver_backend(), solve_for_transaction() |
| Binary discovery | `conda_global/binaries.py` | Copy the two functions (~55 lines) |
| Plugin registration | `conda_global/plugin.py` | Follow same hookimpl pattern |
| Standalone console script | `uv` / `uvx` pattern | `ce` entry point delegates to same CLI handler as `conda exec` |
| CLI with REMAINDER args | `conda/cli/main_run.py:88` | argparse REMAINDER for tool args passthrough |
| Path layout with env override | `conda_global/paths.py` | Same pattern but with `~/.conda/exec` and CONDA_EXEC_HOME |
| Project scaffolding | `conda_global/pyproject.toml` | Mirror structure: hatchling, pixi, ruff, pytest configs |
| PEP 723 parsing | `uv` / `pipx` / `hatch` | All implement `# /// script` block parsing; reference for edge cases |
| Inline metadata spec | [PEP 723](https://peps.python.org/pep-0723/) | Accepted standard for `# /// script` TOML blocks in Python scripts |
| External deps metadata | [PEP 725](https://peps.python.org/pep-0725/) (Draft) | `[external]` table for non-PyPI deps; forward compat target |
| Dep name registry | [PEP 804](https://peps.python.org/pep-0804/) (Draft) | DepURL-to-package mapping; conda-forge is a primary test ecosystem |
| PyPI-in-conda install | `conda_pypi/main.py` | `dry_run_pip_json()`, wheel-to-conda conversion pipeline |
| Script execution prior art | `pelson/conda-execute` | YAML-in-comments format, SHA-256 hashed envs, auto-GC after 25h |
| Ephemeral exec proposal | `conda/conda#13538` | `conda run -x` proposal by @jaimergp; stale, never implemented |

## Verification

### Phases 1-5 (DONE)
1. `pixi run lint && pixi run format-check` -- passes
2. `pixi run -e test pytest` -- all 164 tests pass (95% coverage)
3. `conda exec ruff check .` -- creates cached env, runs ruff, exits with ruff's exit code
4. `ce ruff check .` -- same via standalone alias
5. Second invocation of `conda exec ruff check .` -- uses cache, no solver invocation
6. Verify `~/.conda/exec/envs/ruff--{hash}/` exists with `conda-meta/` inside
7. Error case: `conda exec nonexistent-pkg` -- clear error message
8. Error case: no conda-rattler-solver -- clear error with install instructions
9. `conda exec --list` -- shows cached environments (table and JSON)
10. `conda exec --clean --dry-run` -- shows what would be removed
11. `conda exec --clean ruff --yes` -- removes ruff cache
12. `conda exec "ruff>=0.4" check .` -- version-constrained via match spec in TOOL arg
13. `conda exec --with pytest ruff check .` -- extra package in environment
14. Different specs for same tool create separate cached environments
15. `conda exec --activate samtools view file.bam` -- full conda activation
16. `conda exec --refresh ruff check .` -- force re-creation

### Phase 5 (DONE)

1. `conda exec script.py` -- parses PEP 723 metadata, creates cached env, runs script
2. Script with only `[tool.conda].dependencies` -- works without conda-pypi
3. Script with top-level `dependencies` (PyPI) -- installs via conda-pypi
4. Script with both conda and PyPI deps -- resolves conda first, then PyPI
5. Script with no metadata block -- runs with current Python, no env creation
6. Script with `requires-python` -- becomes a python version spec in the environment
7. Cache reuse -- same metadata block reuses cached environment
8. `conda exec --clean` -- cleans script-based cached environments alongside tool-based ones
9. Error case: PyPI deps declared but conda-pypi not installed -- clear error with install hint
10. `conda exec --with numpy script.py` -- CLI extras merged with script metadata
11. `conda exec --refresh script.py` -- force re-creation of script environment
