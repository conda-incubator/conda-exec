# AGENTS.md -- conda-exec coding guidelines

## Project structure

- The package provides the `conda exec` subcommand via a conda plugin
  and a standalone `ce` command via a console script entry point. Both
  dispatch to the same CLI handler.

- All modules live at the package root. `cli.py` contains parser
  configuration and dispatch. `execute.py` handles the run command.
  `list.py` and `clean.py` handle `--list` and `--clean` flags.
  `format.py` provides display formatting utilities.

- Other core modules handle distinct concerns: `cache.py`
  (ephemeral environment lifecycle and cache key hashing),
  `binaries.py` (executable discovery), `run.py` (subprocess
  execution), `paths.py` (filesystem layout), `exceptions.py`
  (all exceptions).

- Tests mirror the source structure. Tests for
  `conda_exec/cache.py` live in `tests/test_cache.py`, tests for
  `conda_exec/cli.py` live in `tests/test_cli.py`.

## Imports

- Use relative imports for all intra-package references
  (`from .cache import CacheManager`,
  `from .exceptions import SolveError`).
  Absolute `conda_exec.*` imports should only appear in tests
  and entry points.

- Inline (lazy) imports are reserved for performance-critical paths
  or optional dependencies. Acceptable cases: `plugin.py` hooks
  (loaded on every `conda` invocation), `cli.py` command dispatch
  (only the chosen handler is loaded). Everywhere else,
  imports belong at the top of the module.

## Dependencies

- Minimize the dependency graph. Prefer stdlib or already-required
  packages over adding new ones.

- Use conda's own APIs where available: `conda.common.path.BIN_DIRECTORY`
  for platform-correct bin directories, `conda.core.prefix_data.PrefixData`
  for environment metadata, `conda.models.match_spec.MatchSpec` for spec
  parsing, `conda.activate` for activation env vars.

- Pin minimum versions in `pyproject.toml` dependencies (e.g.,
  `"platformdirs >=4.0"`), not exact versions.

## Code structure

- Avoid private module-level helper functions (`_foo()`). If a helper
  is called once, inline it at the call site. If it is genuinely
  reused or tested independently, make it a public function with a
  clear name and docstring. The underscore-prefix convention creates
  untestable, hard-to-patch indirection without real encapsulation.

- Do not use section header comments (e.g.,
  `# --------------- section name ---------------`). Well-named
  functions and clear module structure make them unnecessary. If a
  file needs section dividers, it should be split into separate
  modules instead.

## Typing and linting

- All code must be typed using modern annotations (`str | None` not
  `Optional[str]`, `list[str]` not `List[str]`).

- Use `ty` for type checking and `ruff` for linting and formatting.
  Both are configured in `pyproject.toml`.

- Use `from __future__ import annotations` in all modules.

## Testing

- Tests are plain `pytest` functions. Do not group tests in classes;
  use module-level functions with descriptive names.

- Never use `unittest.mock`, `MagicMock`, `patch`, `Mock`, or any
  other `mock` library. Use `pytest` native fixtures (`tmp_path`,
  `monkeypatch`, `capsys`, `tmp_path_factory`) and real fakes. Build
  small local classes or `monkeypatch.setattr` with recording
  closures when a test needs to observe calls.

- Use `pytest.mark.parametrize` extensively. When multiple test cases
  exercise the same logic with different inputs, consolidate them
  into a single parameterized test with `ids=[...]`. Stack multiple
  `@pytest.mark.parametrize` decorators to cross-product independent
  axes.

- Put shared setup in fixtures, not in repeated inline code. Shared
  fixtures belong in `conftest.py` at the appropriate level.

- After adding or modifying tests or production code, always run the
  full test suite (`pixi run -e test pytest`) and both
  `pixi run ruff check` and `pixi run ruff format --check` to verify
  the changes pass. Fix any lint or formatting issues before
  considering work done.

- Coverage is measured with `pytest-cov`. Run
  `pixi run -e test test-cov` to generate a coverage report.

## Conda integration -- batteries included

- Always reuse conda's built-in APIs before writing custom code.
  conda is a large project with many utilities. Before implementing
  any functionality, check whether conda already provides it:

  - `conda.common.path.BIN_DIRECTORY` for platform-correct bin dirs
  - `conda.common.compat.on_win` for platform detection
  - `conda.core.prefix_data.PrefixData` for environment metadata,
    file listings (`PrefixRecord.files`), timestamps (`.created`,
    `.last_modified`), and size (`.size()`)
  - `conda.models.match_spec.MatchSpec` for spec parsing
  - `conda.models.channel.Channel` for channel objects
  - `conda.activate.PosixActivator` / `CmdExeActivator` for
    activation env vars as dicts (`.build_activate()`)
  - `conda.core.envs_manager.unregister_env` for env cleanup
  - `conda.gateways.disk.delete.rm_rf` for safe recursive deletion
  - `conda.exceptions.CondaError` as the base for all plugin errors
  - `conda.reporters.confirm_yn` for yes/no confirmation prompts
    (respects `context.always_yes` and `context.dry_run` globally)
  - `conda.base.context.context` for global settings like
    `dry_run`, `always_yes`, `json`

  Do not reimplement platform detection, path construction,
  confirmation prompts, or config parsing when conda already
  handles it.

- The plugin registers via `pluggy` hooks (`conda_subcommands`) and
  the `[project.entry-points.conda]` entry point.

- Solver invocation follows the pattern from `conda_global/envs.py`:
  `context.plugin_manager.get_cached_solver_backend()`, `MatchSpec`,
  `Channel`, `solve_for_transaction()`.

## Security

- Never pass unsanitized user input to shell commands. Use
  `subprocess.run` with list arguments, never shell=True.

- Validate all file sizes before deserialization. Cap collection
  sizes to prevent memory exhaustion.

- Use atomic file writes (tempfile + rename) for any state files.

- Limit candidate output counts to prevent terminal flooding.

## Performance

- Plugin load must stay under 1ms. All heavy imports are deferred
  to inside hook functions.

- Cache lookups (checking if an environment exists) must be
  sub-millisecond. Only stat the directory, don't load PrefixData
  for existence checks.

- Solver invocation is the expensive path. Cache aggressively via
  hash-keyed environment directories.

## Documentation

- Docs use Sphinx with `conda-sphinx-theme`, `myst-parser`, and
  `sphinx-design`.

- Follow the Diataxis framework: tutorials, how-to guides, reference,
  and explanation sections.

## Lockfile maintenance

- After any change to `pyproject.toml` that affects pixi metadata
  (dependencies, features, tasks, or workspace settings), run
  `pixi lock` and commit the updated `pixi.lock` alongside the
  `pyproject.toml` change.
