"""Hygiene: business time only comes from app.clock (BUILD_PLAN §4.6)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCAN_DIRS = ("app", "scripts")
BANNED = (
    re.compile(r"date\.today\("),
    re.compile(r"datetime\.now\("),
    re.compile(r"datetime\.utcnow\("),
    re.compile(r"time\.time\("),
)
SQL_NOW = re.compile(r"(?<![\w.])now\(\)")
SQL_CURRENT_DATE = re.compile(r"CURRENT_DATE", re.IGNORECASE)
SQL_CONTEXT = re.compile(r"\b(SELECT|UPDATE|INSERT|DELETE|WHERE|SET|VALUES|AND|OR)\b", re.I)
ALLOW = "real-time-ok"


def _python_files():
    for directory in SCAN_DIRS:
        yield from sorted((ROOT / directory).rglob("*.py"))


def test_no_banned_time_calls_outside_the_clock():
    violations = []
    for path in _python_files():
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if ALLOW in line:
                continue
            for pattern in BANNED:
                if pattern.search(line):
                    violations.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
            if SQL_CURRENT_DATE.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
            elif SQL_NOW.search(line) and SQL_CONTEXT.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    assert violations == [], "banned time calls:\n" + "\n".join(violations)


def test_the_guard_can_fail():
    sample = "x = datetime.now()"
    assert any(pattern.search(sample) for pattern in BANNED)
