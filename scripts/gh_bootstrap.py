#!/usr/bin/env python3
"""Bootstrap GitHub labels, milestones, issues and branch protection (A-09).

Run once after base-v1 is pushed, from the repository root:

    python scripts/gh_bootstrap.py            # do it
    python scripts/gh_bootstrap.py --dry-run  # print the commands only

The script is idempotent: labels use --force, milestones and issues are matched
by title before creating.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "docs" / "tasks"

LABELS = [
    ("owner:A", "1C1B17", "Lead: base, access, integration"),
    ("owner:B", "23405E", "Engine: billing, discounts, lifecycle"),
    ("owner:C", "2E5E3E", "Catalog, subscriptions, design system"),
    ("owner:D", "A8322A", "Money, reporting, ops"),
    ("tier:0", "A8322A", "Required - never cut"),
    ("tier:1", "B9B196", "Should have"),
    ("tier:2", "55524A", "Nice to have"),
    ("request", "23405E", "Request a change in a path you do not own"),
    ("blocked", "A8322A", "Blocked - see the comment for what was tried"),
    ("contract-change", "A8322A", "A §12 signature changes"),
    ("decision", "55524A", "Needs a docs/DECISIONS.md entry"),
    ("unassigned", "2E5E3E", "Free work - self-assign"),
    ("freeze-fix", "1C1B17", "Bug fix during freeze"),
]

MILESTONES = [
    ("G0 base-0a", "Schema, skeleton app, contract stubs, CI, Makefile pushed."),
    ("G1 base-v1", "Login works, main is protected, issues exist, make check green on a clean clone."),
    ("G2 g2-slice", "One scripted path works on main: signup to payment to dashboard."),
    ("G3 g3-complete", "All Tier 0 features merged, e2e and RBAC tests green on main."),
    ("G4 g4-hardened", "Scale seed loaded, perf under budget, integrity all green, style pass done."),
    ("FREEZE freeze", "No features after this. Bug fixes only, PR label freeze-fix."),
]

TASK_LINE = re.compile(r"^- \[[ x]\] ([A-D]-\d+) \(\d+\) (.*)$")


def run(args: list[str], stdin: str | None = None, dry_run: bool = False) -> str:
    print("+ " + " ".join(args))
    if dry_run:
        if stdin:
            print(stdin)
        return ""
    result = subprocess.run(args, input=stdin, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def repo_name(dry_run: bool) -> str:
    return run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], dry_run=dry_run
    )


def ensure_labels(dry_run: bool) -> None:
    for name, color, description in LABELS:
        run(
            ["gh", "label", "create", name, "--color", color, "--description", description, "--force"],
            dry_run=dry_run,
        )


def existing_milestones(repo: str, dry_run: bool) -> set[str]:
    if dry_run:
        return set()
    output = run(
        ["gh", "api", f"repos/{repo}/milestones?state=all&per_page=100", "--jq", ".[].title"]
    )
    return {line for line in output.splitlines() if line}


def ensure_milestones(repo: str, dry_run: bool) -> None:
    have = existing_milestones(repo, dry_run)
    for title, description in MILESTONES:
        if title in have:
            continue
        run(
            [
                "gh",
                "api",
                "-X",
                "POST",
                f"repos/{repo}/milestones",
                "-f",
                f"title={title}",
                "-f",
                f"description={description}",
            ],
            dry_run=dry_run,
        )


def existing_issue_titles(dry_run: bool) -> set[str]:
    if dry_run:
        return set()
    output = run(
        ["gh", "issue", "list", "--state", "all", "--limit", "500", "--json", "title", "--jq", ".[].title"]
    )
    return {line for line in output.splitlines() if line}


def task_rows() -> list[tuple[str, str, str, int]]:
    """(owner, task_id, text, tier) from docs/tasks/<handle>.md."""
    rows = []
    for path in sorted(TASKS_DIR.glob("*.md")):
        owner = path.stem.upper()
        for line in path.read_text().splitlines():
            match = TASK_LINE.match(line)
            if not match:
                continue
            task_id, text = match.group(1), match.group(2).strip()
            tier = 2 if "Tier 2" in text else 1 if "Tier 1" in text else 0
            rows.append((owner, task_id, text, tier))
    return rows


def ensure_issues(dry_run: bool) -> None:
    titles = existing_issue_titles(dry_run)
    for owner, task_id, text, tier in task_rows():
        label_text = re.sub(r"^Tier [12]:\s*", "", text)
        title = f"{task_id}: {label_text}"[:240]
        if any(existing.startswith(task_id + ":") for existing in titles):
            continue
        body = (
            f"Task `{task_id}` for owner {owner} (Tier {tier}).\n\n"
            f"{text}\n\n"
            f"Source: `docs/tasks/{owner.lower()}.md` (BUILD_PLAN §17).\n"
        )
        run(
            [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                f"owner:{owner}",
                "--label",
                f"tier:{tier}",
            ],
            dry_run=dry_run,
        )


def protect_main(repo: str, dry_run: bool) -> None:
    payload = json.dumps(
        {
            "required_status_checks": {"strict": True, "contexts": ["ci"]},
            "enforce_admins": False,
            "required_pull_request_reviews": {
                "required_approving_review_count": 0,
                "dismiss_stale_reviews": False,
            },
            "restrictions": None,
            "allow_force_pushes": False,
            "allow_deletions": False,
            "required_conversation_resolution": False,
        }
    )
    run(
        [
            "gh",
            "api",
            "-X",
            "PUT",
            f"repos/{repo}/branches/main/protection",
            "--input",
            "-",
        ],
        stdin=payload,
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap GitHub labels, issues and protection")
    parser.add_argument("--dry-run", action="store_true", help="print commands without running them")
    args = parser.parse_args(argv)

    if shutil.which("gh") is None:
        print("gh: the GitHub CLI is not installed; install it and run `gh auth login`")
        return 2

    repo = repo_name(args.dry_run)
    print(f"repository: {repo or '(dry run)'}")
    ensure_labels(args.dry_run)
    ensure_milestones(repo, args.dry_run)
    ensure_issues(args.dry_run)
    protect_main(repo, args.dry_run)
    print(
        f"gh-bootstrap: {len(LABELS)} labels, {len(MILESTONES)} milestones, "
        f"{len(task_rows())} tasks, branch protection on main"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
