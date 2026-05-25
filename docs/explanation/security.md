# Security model

conda-exec runs arbitrary binaries from automatically created environments. This is inherently a trust decision, and the security model is designed to be transparent about what is and is not protected.

## Trust boundaries

```{warning}
conda-exec trusts your configured channels completely. Running
`conda exec sometool` downloads and executes binaries from those channels
without additional verification. Only use channels you trust, and be
careful when adding third-party channels via `--channel` or
`[tool.conda].channels` in script metadata.
```

conda-exec trusts the conda solver and the configured package repositories. If a user runs `conda exec ruff`, they are trusting that the `ruff` package from their configured channels (typically conda-forge) contains what it claims. conda-exec does not add verification beyond what conda itself provides. Channel trust, package signatures, and repository integrity are all delegated to conda's own security model.

What conda-exec *does* control is everything that happens after packages are installed into the cache: which binary gets executed, how it is invoked, and what environment it runs in.

## Binary discovery and symlink safety

When you run `conda exec ruff`, conda-exec looks for a binary named `ruff` in the cached environment's `bin/` directory (or `Scripts/` on Windows). The critical question is: does that binary actually live inside the environment?

A malicious or misconfigured package could install a symlink that points outside the prefix. For example, a binary at `prefix/bin/ruff` could be a symlink to `/usr/bin/something-dangerous`. Without validation, conda-exec would happily execute whatever the symlink points to.

The `find_binary()` function prevents this. After locating a candidate binary, it resolves the full path through any symlinks and checks that the resolved path is still within the environment prefix using `is_within_prefix()`:

```python
def is_within_prefix(path: Path, resolved_prefix: Path) -> bool:
    try:
        return path.resolve().is_relative_to(resolved_prefix)
    except (OSError, ValueError):
        return False
```

If the resolved binary escapes the prefix, `find_binary()` returns `None` and the tool invocation fails with a "command not found" error rather than executing an unexpected binary. Errors during resolution (broken symlinks, permission issues) are also treated as failures, defaulting to the safe outcome.

The prefix itself is resolved once by the caller and passed in, so the comparison is always between two fully resolved paths. This avoids TOCTOU (time-of-check-time-of-use) issues where the prefix path might be interpreted differently at check time versus use time.

## Subprocess execution

conda-exec invokes tools using `subprocess.run` with a list of arguments:

```python
subprocess.run([str(binary), *args], env=env)
```

On Unix and for native Windows executables (`.exe`), this is not a shell invocation. The binary path and all arguments are passed directly to the operating system's process creation APIs, bypassing shell interpretation.

On Windows, `.bat` and `.cmd` launchers are batch scripts. Python may route those through `cmd.exe` even when `shell=False`, so their argument handling follows Windows batch-file rules. conda-exec prefers `.exe` over `.bat` and `.cmd` when multiple launchers exist, but users should treat batch-backed tools as having a weaker shell-injection boundary than native executables.

The only modification to the subprocess environment is PATH manipulation. In the default mode, the prefix's `bin/` directory is prepended to PATH so the tool can find its own dependencies. With `--activate`, conda's activator is used to build environment variables such as `CONDA_PREFIX`.

## Cache key validation

Cache keys control which directory on disk an environment maps to. If a cache key could be manipulated to contain path traversal sequences, an attacker could potentially read from or write to arbitrary filesystem locations.

Three layers of validation prevent this:

1. `SAFE_TOOL_RE` only allows `[a-zA-Z0-9_][a-zA-Z0-9_.+-]*`. This rules out `/`, `..`, null bytes, and other characters that have special meaning in file paths.

2. `SAFE_KEY_RE` validates the complete `{tool}--{hash}` format, ensuring the hash portion contains only hex digits.

3. Even if a key somehow passes both regexes, `prefix_for()` resolves the constructed path and verifies it is within the envs directory using `is_relative_to()`. This is the final safety net. On case-insensitive filesystems, Unicode normalization edge cases, or any other situation where regex validation might be insufficient, the resolved path check catches the escape.

Keys are also length-limited to 200 characters to prevent filesystem issues and potential buffer-related problems on platforms with strict path length limits.

## File size limits

When parsing PEP 723 inline metadata from script files, conda-exec checks the file size before reading. Files larger than 10 MB are skipped entirely, and `parse_script_metadata()` returns `None`.

This prevents memory exhaustion if conda-exec is pointed at a large binary file or a generated data file that happens to have a `.py` extension. Without this limit, reading a multi-gigabyte file into memory to search for a metadata block would be a denial-of-service risk, particularly in automated pipelines.

## Atomic file operations

Environment creation uses a temporary directory with atomic rename to prevent two categories of problems:

If the download or extraction fails midway, the temporary directory is cleaned up. No other process can observe a half-built environment at the final cache path, because the final path only appears after the atomic rename succeeds.

If two processes attempt to create the same environment simultaneously, only one rename succeeds. The other process detects the existing valid environment and uses it. This prevents corruption from concurrent writes without requiring explicit file locking, which is notoriously unreliable across platforms and filesystems.

Temporary directories are prefixed with `.tmp-` and are explicitly excluded from cache enumeration in `list_cached()`, so they never appear in `--list` output even if a crash leaves one behind.

## No shell activation by default

When conda-exec runs a tool, it does *not* compute activation environment variables by default. It only prepends the environment's `bin/` directory to PATH:

```python
env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
```

Activation mode, triggered by the `--activate` flag, uses conda's activation logic to compute environment variables like `CONDA_PREFIX` and `CONDA_DEFAULT_ENV`. conda-exec does not invoke a shell activation script for the parent process.

If a package requires `activate.d/` shell scripts, use a named conda environment with `conda run` or an explicitly activated shell instead. conda-exec's activation mode is intended for tools that need activation environment variables, not tools that depend on shell-script side effects.

The default PATH-only mode keeps the subprocess environment small. Most CLI tools (linters, formatters, compilers) do not need activation and work correctly with just PATH. By making activation opt-in, conda-exec reduces the amount of environment rewriting done by default. Users who need activation variables (for tools that depend on `CONDA_PREFIX` or package-specific environment variables) can explicitly request them.

## Environment isolation

Each unique combination of specs and channels produces a separate cached environment. Environments are never shared between different spec combinations, even if one is a subset of another. `conda exec ruff` and `conda exec ruff --with black` create two independent environments.

This prevents interference between tool invocations. A tool cannot be affected by packages that were installed for a different invocation, and removing one cached environment has no effect on others.

The isolation also means that cached environments are self-contained conda prefixes. They have their own `conda-meta/`, their own package records, and their own binary directories. There is no shared state between environments beyond the filesystem directory that contains them.

## Summary of guarantees

| Threat | Mitigation |
|--------|-----------|
| Symlink escape from prefix | `is_within_prefix()` resolves and validates binary paths |
| Shell injection via tool name or args | `subprocess.run` with list arguments; native executables bypass shell parsing |
| Path traversal via cache key | Regex validation + resolved path `is_relative_to()` check |
| Partial environment on crash | Atomic `tempfile.mkdtemp` + `os.rename` |
| Memory exhaustion from large scripts | 10 MB file size limit on script parsing |
| Activation environment side effects | PATH-only mode by default, activator env vars opt-in via `--activate` |
| Cross-environment interference | Fully isolated prefixes per spec combination |
| Concurrent environment creation | Atomic rename with fallback to existing environment |
