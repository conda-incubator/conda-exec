# /// script
# requires-python = ">=3.11"
#
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["python-dateutil>=2.9"]
# ///

from __future__ import annotations

import sys

from dateutil.parser import parse


def main() -> int:
    raw = sys.argv[1] if len(sys.argv) > 1 else "May 28, 2026 10:30"
    parsed = parse(raw)
    print(f"{parsed:%A, %B %d, %Y}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
