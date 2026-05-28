# Pin package versions

conda-exec accepts version constraints as part of the tool argument, using
conda's match spec syntax.

## Bare package name

With no constraint, the solver chooses a compatible available version:

```bash
conda exec ruff check .
```

## Single version constraint

```{note}
Always quote match specs that contain version operators (`>`, `<`, `=`,
`!`). Without quotes, the shell may interpret these characters as
redirections or other special syntax.
```

Quote the tool argument when it contains a version specifier:

```bash
conda exec "ruff>=0.4" check .
```

The binary name (`ruff`) is extracted from the match spec automatically.

## Multiple constraints

Combine constraints with commas for a version range:

```bash
conda exec "ruff>=0.4,<0.5" check .
```

## Exact version

Pin to an exact version:

```bash
conda exec "ruff==0.4.3" check .
```

## Add extra packages with --with

Use `--with` to install additional packages alongside the tool. Each
`--with` value is a full match spec:

```bash
conda exec --with "python=3.12" jupyter lab
conda exec --with pytest --with hypothesis ruff check .
```

## How specs affect caching

Each unique combination of specs and channels produces a different cache
key. These three invocations create three separate cached environments:

```bash
conda exec ruff check .                    # ruff--<hash1>
conda exec "ruff>=0.4" check .             # ruff--<hash2>
conda exec --with pytest ruff check .      # ruff--<hash3>
```

This means you can have multiple versions of the same tool cached
simultaneously without conflicts.

## Force re-creation

If a cached environment is outdated or you want to pick up a newly released
version, use `--refresh` to discard the existing cache and solve again:

```bash
conda exec --refresh ruff check .
```

This removes the cached environment for that specific spec/channel
combination and creates a fresh one.
