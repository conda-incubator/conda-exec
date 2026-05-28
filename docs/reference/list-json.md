# Cache list JSON

`conda exec --list --json` prints machine-readable cache metadata when
cached environments exist.

```bash
conda exec --list --json
```

The standalone alias has the same output:

```bash
ce --list --json
```

## Output shape

The output is a JSON array. Each item describes one cached environment:

```json
[
  {
    "tool": "ruff",
    "key": "ruff--a3f8b2c140d91a4e",
    "prefix": "/Users/alice/.conda/exec/envs/ruff--a3f8b2c140d91a4e",
    "created": "2026-05-28T09:15:23.123456+00:00",
    "last_used": "2026-05-28T10:42:01.987654+00:00",
    "size_bytes": 44983910,
    "packages": 3
  }
]
```

## Fields

`tool`
: The tool portion of the cache key. Tool environments use the package
  name, and script environments use `script`.

`key`
: The full cache key, including the hash suffix.

`prefix`
: Absolute path to the cached conda prefix.

`created`
: ISO 8601 timestamp from conda's prefix metadata, or `null` when the
  creation time is unavailable.

`last_used`
: ISO 8601 timestamp from conda's prefix metadata, or `null` when the
  timestamp is unavailable. conda-exec updates the environment history
  mtime on cache hits with a one-hour debounce.

`size_bytes`
: Size of the prefix in bytes as reported by conda's
  {py:class}`~conda.core.prefix_data.PrefixData`.

`packages`
: Number of package records in the environment.

## Empty cache behavior

When no cached environments exist, the command prints the same text as the
table output:

```text
No cached environments.
```

Do not assume empty output is valid JSON. If a script needs to handle both
cases, treat this exact message as an empty list or ensure at least one
cache entry exists before consuming JSON.

## Relationship to conda JSON mode

Use the local `--json` flag with `--list`. conda-exec's list output is not
currently controlled by conda's global `CONDA_JSON` setting.

`--json` is only meaningful with `--list`. Passing it to a normal tool or
script run prints a warning and continues without changing the tool output.
