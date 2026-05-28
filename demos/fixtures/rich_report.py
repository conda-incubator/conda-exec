# /// script
# requires-python = ">=3.11"
# dependencies = ["rich>=13"]
#
# [tool.conda]
# channels = ["conda-forge"]
# dependencies = ["python-dateutil>=2.9"]
# ///

from __future__ import annotations

from dateutil.parser import parse
from rich.console import Console
from rich.table import Table


def main() -> int:
    parsed = parse("May 28, 2026 10:30")

    table = Table(title="conda-exec script metadata")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("PyPI dependency", "rich")
    table.add_row("conda dependency", "python-dateutil")
    table.add_row("parsed date", f"{parsed:%A, %B %d, %Y}")
    Console().print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
