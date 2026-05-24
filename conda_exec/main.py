"""Entry point for the ``ce`` standalone command."""

from __future__ import annotations

import sys
from argparse import ArgumentParser

from .cli import configure_parser, execute


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(
        prog="ce",
        description="Run a command from a conda package without installing it.",
    )
    configure_parser(parser)
    args = parser.parse_args(argv)
    return execute(args)


if __name__ == "__main__":
    sys.exit(main())
