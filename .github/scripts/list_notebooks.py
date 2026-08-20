"""List notebooks that should be tested by CI.

Walks all `*.ipynb` in the repo, subtracts entries matching any pattern in
`.github/notebook-test-exclusions.txt`. Optionally intersects with a list of
changed files (for the per-PR workflow) supplied on stdin.

Output is JSON (an array of paths), suitable for a GitHub Actions matrix.

Usage:
    python .github/scripts/list_notebooks.py [--changed-only]

When `--changed-only` is passed, the script reads newline-separated changed
file paths from stdin and intersects with the walked set before applying
exclusions.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXCLUSIONS_FILE = REPO_ROOT / ".github" / "notebook-test-exclusions.txt"


def load_exclusions() -> list[str]:
    if not EXCLUSIONS_FILE.exists():
        return []
    return [
        line.strip()
        for line in EXCLUSIONS_FILE.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def is_excluded(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(path, pat):
            return True
        # Also support /** style matches by stripping the trailing /** and
        # checking prefix
        if pat.endswith("/**") and (path == pat[:-3] or path.startswith(pat[:-2])):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Read newline-separated changed file paths from stdin and "
             "restrict output to changed files that are also .ipynb",
    )
    args = parser.parse_args()

    exclusions = load_exclusions()

    if args.changed_only:
        candidates = [
            line.strip()
            for line in sys.stdin.read().splitlines()
            if line.strip().endswith(".ipynb")
        ]
        # Drop paths that no longer exist (deleted in the PR)
        candidates = [p for p in candidates if (REPO_ROOT / p).exists()]
    else:
        candidates = sorted(
            str(p.relative_to(REPO_ROOT))
            for p in REPO_ROOT.rglob("*.ipynb")
            if ".ipynb_checkpoints" not in p.parts
        )

    notebooks = [p for p in candidates if not is_excluded(p, exclusions)]
    print(json.dumps(notebooks))


if __name__ == "__main__":
    main()
