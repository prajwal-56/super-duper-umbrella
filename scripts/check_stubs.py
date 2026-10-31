#!/usr/bin/env python3
"""Report CONTRACT-STUB placeholders (BUILD_PLAN §4.4, §12).

`make check-stubs` fails while any stub remains; `make check` runs it with
--report so the count is visible but does not block during the build.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("app", "scripts")
MARKER = re.compile(r"CONTRACT-STUB owner=([A-D])")


def scan() -> dict[str, list[str]]:
    """Return {owner: [file:line, ...]} for every stub marker found."""
    found: dict[str, list[str]] = {}
    for directory in SCAN_DIRS:
        base = ROOT / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            for number, line in enumerate(path.read_text().splitlines(), start=1):
                match = MARKER.search(line)
                if match:
                    found.setdefault(match.group(1), []).append(
                        f"{path.relative_to(ROOT)}:{number}"
                    )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report contract stubs")
    parser.add_argument(
        "--report",
        action="store_true",
        help="always exit 0 (used by make check while the build is in progress)",
    )
    args = parser.parse_args(argv)

    found = scan()
    total = sum(len(locations) for locations in found.values())
    for owner in sorted(found):
        print(f"owner {owner}: {len(found[owner])} stub marker(s)")
        for location in found[owner]:
            print(f"  {location}")
    print(f"check-stubs: {total} stub marker(s) remaining")
    if total and not args.report:
        print("check-stubs: FAIL (replace stubs before freeze)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
