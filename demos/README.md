# Demo recordings

Animated terminal demos recorded with [VHS](https://github.com/charmbracelet/vhs).

This directory follows the same pattern used by the sibling
`conda-completion` and `conda-workspaces` projects: shared VHS settings,
small fixture files, source tapes committed beside the generated media, and
one `pixi run demos` task for batch recording.

## Primary demos

| Demo | Diataxis fit | Description |
|---|---|---|
| `quickstart` | Tutorial | First tool run, cache reuse, the `ce` alias, and `--list`. |
| `extra-packages` | How-to | Add runtime dependencies with `--with` and pass tool arguments after `--`. |
| `script-dependencies` | Tutorial | Run a PEP 723 script that declares conda dependencies inline. |
| `script-lock` | How-to | Generate a sidecar script lock, clean the cache, and run from lock data. |
| `cache-management` | How-to / reference | Inspect table and JSON cache listings, preview cleanup, then clean. |
| `pypi-script` | How-to | Run a PEP 723 script that mixes PyPI dependencies and conda dependencies. |

Together these cover the core conda-exec user experience:

- one-off command execution without permanently installing tools
- cache miss versus cache hit behavior
- the short `ce` command for interactive use
- conda package specs plus extra runtime packages
- inline script dependency metadata
- repeatable script execution through lock data
- disposable cache inspection and cleanup
- the conda/PyPI bridge when `conda-pypi` is installed

## Deferred candidates

These are useful later, but are intentionally not part of the default batch
because they are longer, domain-specific, or need curated sample data:

| Demo | Why it matters |
|---|---|
| `channels-bioconda` | Show `-c conda-forge -c bioconda samtools ...` for domain channels. |
| `activation` | Show `--activate` for tools that inspect `CONDA_PREFIX` or activation vars. |
| `embedded-lock` | Show `conda exec --lock --embed script.py` for single-file sharing. |
| `ci-cache` | Show `CONDA_EXEC_HOME` and package cache reuse in CI jobs. |
| `error-recovery` | Show actionable errors for missing `conda-pypi`, missing binaries, and stale locks. |

## Prerequisites

- [VHS](https://github.com/charmbracelet/vhs) (`brew install vhs` or
  `go install github.com/charmbracelet/vhs@latest`)
- [ttyd](https://github.com/tsl0922/ttyd), installed automatically by VHS
  on first run
- [bat](https://github.com/sharkdp/bat) for readable source listings
- a working `pixi` installation with the `dev` and `test` environments
  installed

The `pypi-script` tape enters the `test` environment because that is where
this project installs `conda-pypi`.

## Regenerating demos

From the project root:

```bash
# Regenerate all demos
pixi run demos

# Regenerate one demo
pixi run demos quickstart
```

Each tape writes both `demos/<name>.gif` and `demos/<name>.mp4`.

## Recording notes

- Each tape uses a temporary `CONDA_EXEC_HOME` under `/tmp` so recordings
  do not mutate the user's normal `~/.conda/exec` cache.
- `CONDA_EXEC_AUTO_CLEAN=false` keeps automatic cleanup from changing the
  state midway through a recording.
- `CONDA_PLUGINS_USE_SHARDED_REPODATA=1` matches the conda-workspaces demo
  setup and keeps solver metadata fetches lighter when supported.
- Generated GIFs are suitable for docs and README embeds. MP4s are higher
  quality for release notes, social previews, or long-form demos.

## File structure

- `_settings.tape` - shared VHS theme, font, dimensions, and environment
  defaults
- `fixtures/` - small scripts copied into temporary recording directories
- `*.tape` - individual demo scripts
- `*.gif` - generated animated GIFs
- `*.mp4` - generated MP4 videos
