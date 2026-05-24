# Changelog

## 0.1.0 (unreleased)

Initial release of conda-exec: ephemeral package execution for conda.

### Highlights

conda-exec lets you run any conda package without installing it permanently.
It creates a cached, isolated environment, runs the tool, and exits. Cached
environments are reused automatically on subsequent runs. Think `npx` for
Node or `uvx` for Python/uv, but for conda packages.

```bash
conda exec ruff check .
ce ruff check .
```

### Features

#### Ephemeral package execution

- Run any conda package by name: `conda exec ruff check .`
- Version constraints via match specs: `conda exec "ruff>=0.4,<0.5" check .`
- Extra packages with `--with`: `conda exec --with pytest ruff check .`
- Custom channels with `-c`: `conda exec -c bioconda samtools view file.bam`
- Force re-creation with `--refresh`: `conda exec --refresh ruff check .`
- Full conda activation with `--activate` for tools that need `CONDA_PREFIX`

#### Standalone `ce` command

- `ce` is a standalone console script alias for `conda exec`
- Works without conda's plugin system, useful for shell scripts and CI
- Identical CLI interface: `ce ruff check .`

#### PEP 723 inline script execution

- Run Python scripts with inline dependency metadata: `conda exec script.py`
- Parses standard PEP 723 `# /// script` metadata blocks
- Supports `requires-python` constraints with validation
- Supports `[tool.conda]` extension for conda-native dependencies and channels
- PyPI dependencies via conda-pypi integration (optional)
- Scripts without metadata run with the current Python (no environment created)
- Shebang support: `#!/usr/bin/env conda-exec` for directly executable scripts

#### Cache management

- `conda exec --list` shows all cached environments with size, age, and
  package count
- `conda exec --list --json` for machine-readable JSON output
- `conda exec --clean` removes environments unused for 30+ days
- `conda exec --clean --all --yes` removes everything without prompting
- `conda exec --clean --older-than 7 ruff` targets specific tools and ages
- `conda exec --clean --dry-run` previews what would be removed
- Last-used tracking via conda-meta/history mtime

#### Security

- Cache keys use SHA-256 hashing of normalized, sorted specs and channels
- Tool names and cache keys validated against strict regex patterns
- Path traversal protection via `is_relative_to()` checks
- Symlink containment: binaries must resolve within the prefix
- Script file size capped at 10 MB to prevent memory exhaustion
- Atomic environment creation via temp directory + rename
- All subprocess calls use list arguments (no shell=True)

#### Cross-platform support

- Linux (x86_64, aarch64), macOS (x86_64, arm64), Windows (x86_64)
- Platform-correct binary discovery using conda's `BIN_DIRECTORY`
- Windows-specific executable extensions (.exe, .bat, .cmd)
- Windows path fallback via `platformdirs` when `~/.conda` is unavailable

### Infrastructure

- CI testing on Linux, macOS, and Windows across Python 3.10 through 3.14
- Performance benchmarks tracked via bencher.dev with regression detection
- GitHub Actions workflows hardened per zizmor audit (SHA-pinned actions,
  `persist-credentials: false`, minimal permissions)
- Dependabot configured for GitHub Actions, pip, and conda ecosystems
- Documentation built with Sphinx, conda-sphinx-theme, and myst-parser,
  following the Diataxis framework
- Release automation via GitHub Actions with PyPI trusted publishing

### Dependencies

- Requires conda >= 25.1
- Requires conda-rattler-solver for fast environment creation
- Optional: conda-pypi for PyPI dependency support in scripts
- Runtime: packaging >= 22.0, tomli >= 1.0 (Python < 3.11)

### Test suite

- 194 tests (168 unit, 26 integration/benchmark)
- No mocking libraries: pure pytest fixtures with real fakes
- pytest-subprocess for subprocess call assertions
- time-machine for deterministic time-dependent tests
- pytest-benchmark for performance regression tracking
