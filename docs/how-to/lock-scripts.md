# Lock script environments

Use lock data when a script needs repeatable environments across cache
cleans, machines, or CI runs.

## Write a sidecar lockfile

Run a metadata-backed script with `--lock`:

```bash
conda exec --lock script.py
```

conda-exec resolves the script environment, runs the script, and writes
lock data next to the script. The default `rattler-lock-v6` format writes:

```text
script.py
script.py.conda-exec.lock
```

Future runs discover the sidecar lockfile automatically:

```bash
conda exec script.py
```

When lock data is available, conda-exec creates the cached environment from
the lock instead of solving from the PEP 723 metadata.

If discovered lock data cannot be used for the current platform and the
script still has metadata, conda-exec warns and falls back to solving from
the metadata.

Lockfiles are trusted input. Only use sidecar or embedded lock data from
repositories and directories you trust.

## Embed lock data in the script

Use `--embed` with `--lock` when the script should remain a single file:

```bash
conda exec --lock --embed script.py
```

This writes a generated `# /// conda-exec-lock` block into the script.

```python
# /// conda-exec-lock
# ...generated lock data...
# ///
```

`--embed` only changes where generated lock data is written. It must be used
with `--lock`.

## Lock multiple platforms

Repeat `--platform` to include multiple conda subdirs:

```bash
conda exec --lock \
  --platform linux-64 \
  --platform osx-arm64 \
  --platform win-64 \
  script.py
```

Embedded locks support the same option:

```bash
conda exec --lock --embed \
  --platform linux-64 \
  --platform osx-arm64 \
  script.py
```

## Refresh lock data

Use `--refresh` with `--lock` to force a fresh solve and update the lock:

```bash
conda exec --lock --refresh script.py
```

To update embedded lock data:

```bash
conda exec --lock --embed --refresh script.py
```

`--refresh` without `--lock` ignores lock data and solves from metadata.

Use `--ignore-lock` to ignore discovered lock data for one run:

```bash
conda exec --ignore-lock script.py
```

## Requirements

Lock support uses conda's environment exporter and specifier plugins. The
default lock format is the `rattler-lock-v6` format provided by
`conda-lockfiles`. conda-exec uses a namespaced sidecar filename for the
default format and uses conda's plugin metadata to create and export lock
data.

If your conda installation cannot read or write that format, install
`conda-lockfiles` in the environment that provides `conda exec`.

```bash
conda install -n base conda-lockfiles
```
