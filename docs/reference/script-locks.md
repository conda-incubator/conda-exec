# Script lock reference

Script lock data records a concrete resolved environment for a script. It
is generated from the script's dependency input and later used to create a
cached environment without solving from metadata.

## Requirements

Lock support uses conda's registered
[environment exporter](https://docs.conda.io/projects/conda/en/stable/dev-guide/plugins/environment_exporters.html)
and
[environment specifier](https://docs.conda.io/projects/conda/en/stable/dev-guide/plugins/environment_specifiers.html)
plugins, both keyed by conda's
{py:class}`~conda.plugins.types.EnvironmentFormat`. The default format is
`rattler-lock-v6`, provided by `conda-lockfiles`.

Install it in the environment that provides `conda exec`:

```bash
conda install -n base -c conda-forge conda-lockfiles
```

If the format is missing, conda-exec raises `ScriptLockError`.

## Commands

Generate or refresh a sidecar lockfile:

```bash
conda exec --lock script.py
conda exec --lock --refresh script.py
```

Embed lock data in the script:

```bash
conda exec --lock --embed script.py
```

Ignore discovered lock data for one run:

```bash
conda exec --ignore-lock script.py
```

Generate lock data for multiple conda subdirs:

```bash
conda exec --lock \
  --platform linux-64 \
  --platform osx-arm64 \
  --platform win-64 \
  script.py
```

`--lock` is only supported for existing script files. `--embed` requires
`--lock`.

## Sidecar filenames

With the default lock format, conda-exec discovers these sidecar names next
to `script.py`:

```text
script.py.conda-exec.lock
script.conda-exec.lock
```

`script.py.conda-exec.lock` is the default write target. The shorter
`script.conda-exec.lock` form is also discovered for compatibility with
common sidecar naming conventions.

For non-default lock formats, sidecar names are derived from the lock
exporter and specifier plugin metadata.

## Embedded block

Embedded lock data uses a generated metadata block:

```python
# /// conda-exec-lock
# # conda-exec-lock-input-sha256: <digest>
# ...lock data...
# ///
```

This block is generated state, not dependency intent. Keep human-authored
requirements in the `# /// script` block.

The digest line has two `#` characters in the script source: one is the
metadata block comment prefix, and one is part of the generated lock
content.

When embedding lock data, conda-exec preserves the script's executable mode
bits and writes the file atomically.

## Discovery order

When running `conda exec script.py`, conda-exec checks:

1. embedded `# /// conda-exec-lock` content already read from the script
2. sidecar lockfiles next to the script
3. the PEP 723 metadata block

Embedded lock data wins because it is part of the single-file artifact.
Sidecar lockfiles are the normal repository workflow.

## When locks are ignored

Discovered lock data is ignored when any of these are present:

- `--ignore-lock`
- `--lock`
- `--refresh`
- `--with`
- `--channel`

Those flags either ask conda-exec to generate new lock data or change the
dependency input for this run. conda-exec solves from metadata instead.

## Input digest

Generated lock data starts with:

```text
# conda-exec-lock-input-sha256: <digest>
```

The digest is computed from:

- script conda channels
- script conda dependencies
- script PyPI dependencies
- `requires-python`
- CLI `--with` specs
- CLI `--channel` values

conda-exec only auto-uses generated lock data when the stored digest
matches the current dependency input. This prevents stale sidecars from
silently overriding changed script metadata.

## Cache keys

Environments created from metadata use a `script--<hash>` key derived from
metadata.

Environments created from lock data also use a `script--<hash>` key, but
the hash is derived from the lock content. Updating lock data creates a new
cached environment.

## Lock size limits

Sidecar and embedded lock data are limited to 10 MB. Larger lockfiles raise
`ScriptLockError`, and oversized embedded locks are not written.

## Fallback behavior

If lock data is discovered but cannot be used, conda-exec behaves
differently depending on whether metadata is available:

- If the script still has a valid `# /// script` block, conda-exec warns and
  falls back to solving from metadata.
- If the script has no metadata, the lock error is fatal because there is no
  dependency input to solve from.

Use `--ignore-lock` when you intentionally want to bypass lock data and
solve from metadata.
