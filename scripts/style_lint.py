#!/usr/bin/env python3
"""Style law enforcement (BUILD_PLAN §15). Fails `make check` on violations."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"

CSS_BANNED = (
    "border-radius",
    "box-shadow",
    "transition",
    "animation",
    "@keyframes",
    "gradient",
)
PURPLE = re.compile(r"purple|indigo|violet|#(?:7c3aed|6d28d9|8b5cf6|6366f1|4f46e5|4338ca)", re.I)
EMOJI = re.compile(
    "[\U0001f000-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff\ufe0f]"
)
ALLOWED_CSS = re.compile(r"^(ledger|mod_[abcd])\.css$")


def _lines(path: Path) -> list[tuple[int, str]]:
    return list(enumerate(path.read_text().splitlines(), start=1))


def lint_html(path: Path) -> list[str]:
    problems: list[str] = []
    for number, line in _lines(path):
        rel = f"{path.relative_to(ROOT)}:{number}"
        if "<script" in line and "window.print()" not in line:
            problems.append(f"{rel}: <script> is banned (only a window.print() button is allowed)")
        if "style=" in line:
            problems.append(f"{rel}: inline style attribute is banned")
        if "<style" in line:
            problems.append(f"{rel}: <style> block is banned")
        if "<img" in line:
            problems.append(f"{rel}: images are banned")
        if EMOJI.search(line):
            problems.append(f"{rel}: emoji are banned in templates")
        if PURPLE.search(line):
            problems.append(f"{rel}: purple/indigo/violet is banned")
    return problems


def lint_css(path: Path) -> list[str]:
    problems: list[str] = []
    for number, line in _lines(path):
        rel = f"{path.relative_to(ROOT)}:{number}"
        lowered = line.lower()
        for token in CSS_BANNED:
            if token in lowered and "style-lint-ok" not in line:
                problems.append(f"{rel}: {token} is banned")
        if PURPLE.search(line):
            problems.append(f"{rel}: purple/indigo/violet is banned")
    return problems


def lint() -> list[str]:
    problems: list[str] = []
    if TEMPLATES.exists():
        for path in sorted(TEMPLATES.rglob("*.html")):
            problems.extend(lint_html(path))
    if STATIC.exists():
        for path in sorted(STATIC.iterdir()):
            if path.suffix == ".css":
                if not ALLOWED_CSS.match(path.name):
                    problems.append(
                        f"{path.relative_to(ROOT)}: only ledger.css and mod_<handle>.css are allowed"
                    )
                problems.extend(lint_css(path))
            elif path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}:
                problems.append(f"{path.relative_to(ROOT)}: images are banned")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the ledger style law")
    parser.add_argument("--report", action="store_true", help="print and always exit 0")
    args = parser.parse_args(argv)

    problems = lint()
    for problem in problems:
        print(problem)
    if problems:
        print(f"style-lint: {len(problems)} violation(s)")
        return 0 if args.report else 1
    print("style-lint: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
