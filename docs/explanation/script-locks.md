# Script lock design

Script metadata describes dependency intent. Lock data records one concrete
resolution of that intent.

conda-exec keeps those concepts separate:

- `# /// script` is human-authored PEP 723 metadata.
- `# /// conda-exec-lock` is generated state.
- sidecar lockfiles are generated state stored outside the script.

This separation keeps scripts understandable while still allowing exact
environment reproduction.

## Sidecar lockfiles by default

`conda exec --lock script.py` writes a sidecar lockfile using the default
filename published by conda's selected lockfile exporter. With the default
`conda-lock-v1` exporter, that is `script.py.conda-lock.yml`.

Sidecar lockfiles are the default because they are visible, easy to review,
and do not mutate source files unexpectedly. They also scale better for
multi-platform locks, which can become large.

## Embedded locks for single-file scripts

`conda exec --lock --embed script.py` writes generated lock data into the
script itself.

Embedded locks are useful when the script is the unit of distribution:

- examples shared as one file
- small scientific utilities
- directly executable `#!/usr/bin/env ce` scripts
- scripts copied between machines without a repository

Because embedding mutates the script file, it is explicit rather than the
default.

## Discovery order

When a script runs, conda-exec checks lock data before solving:

1. embedded `# /// conda-exec-lock` block
2. script-specific sidecar files derived from the exporter default filenames
3. PEP 723 metadata solve

Embedded data wins because a single-file artifact should be self-contained.
Sidecar lockfiles remain the normal project/repository workflow.

## Cache identity

Environments created from lock data use a `script--{hash}` cache key derived
from the lock content. This means changing lock data creates a different
cached environment, even if the PEP 723 metadata block stays the same.

Environments created from metadata keep using the metadata-derived cache key.
That preserves the existing fast path for scripts without lock data.
