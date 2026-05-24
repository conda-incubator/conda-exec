"""Execute a tool from an ephemeral conda environment."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

DEFAULT_CHANNELS = ["conda-forge"]


def execute_run(args: Namespace) -> int:
    """Execute a tool from an ephemeral conda environment."""
    from conda.models.match_spec import MatchSpec

    from ..binaries import find_binary
    from ..cache import CacheManager
    from ..exceptions import BinaryNotFoundError, CondaExecError
    from ..run import run_in_prefix

    tool = args.tool
    if not tool:
        print("conda exec: missing TOOL argument", file=sys.stderr)
        print("usage: conda exec [OPTIONS] TOOL [ARGS...]", file=sys.stderr)
        print("       conda exec list", file=sys.stderr)
        print("       conda exec clean", file=sys.stderr)
        return 2

    name = MatchSpec(tool).name
    channels = args.channels or DEFAULT_CHANNELS
    specs = [tool] + (args.with_specs or [])

    tool_args = args.tool_args or []
    if tool_args and tool_args[0] == "--":
        tool_args = tool_args[1:]

    try:
        cache = CacheManager()
        key = cache.cache_key(name, specs, channels)

        if args.refresh:
            cache.remove(key)

        cached = cache.exists(key)
        if not cached:
            print(
                f"Creating environment for {name}...",
                end="",
                file=sys.stderr,
                flush=True,
            )
            t0 = time.monotonic()

        prefix = cache.get_or_create(key, specs, channels)

        if not cached:
            elapsed = time.monotonic() - t0
            print(f" done ({elapsed:.1f}s)", file=sys.stderr, flush=True)

        binary = find_binary(prefix, name)
        if binary is None:
            raise BinaryNotFoundError(name, str(prefix))

        return run_in_prefix(prefix, binary, tool_args, activate=args.activate)

    except CondaExecError as exc:
        print(f"conda exec: {exc.error_message}", file=sys.stderr)
        if hasattr(exc, "hints") and exc.hints:
            for hint in exc.hints:
                print(f"  hint: {hint}", file=sys.stderr)
        return 1
