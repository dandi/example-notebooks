"""Refresh `.github/colab-preinstalled.txt` from Colab's published pip freeze.

Colab rebuilds its runtime image every week or two, and each rebuild bumps some
of the preinstalled packages. The notebooks' install cells are locked against
the snapshot in `.github/colab-preinstalled.txt`, so once the snapshot is stale
the install cell downgrades those packages back to the old pins, which is slow
and forces a runtime restart. This script rewrites the snapshot from
googlecolab/backend-info and, with `--relock`, re-locks every notebook that
already has a bootstrap install cell and is tested by CI.

Only `name==version` lines are kept. Colab's freeze also lists direct-URL
installs (torch, google-colab, ...), which cannot be used as constraints.

Usage:
    python .github/scripts/refresh_colab_snapshot.py [--relock]

Exits 0 whether or not anything changed; prints `changed=true|false` and, when
$GITHUB_OUTPUT is set, writes the same line there.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import nbformat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from list_notebooks import REPO_ROOT, is_excluded, load_exclusions  # noqa: E402
from lock_notebook import CONSTRAINT, requirements_for  # noqa: E402
from run_notebook import find_install_cell  # noqa: E402

SOURCE_URL = "https://raw.githubusercontent.com/googlecolab/backend-info/main/pip-freeze.txt"
PIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*==\S+$")
REFRESHED_RE = re.compile(r"^# Last refreshed: .*$", re.MULTILINE)


def fetch_pins() -> list[str]:
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as r:
        text = r.read().decode()
    pins = [line.strip() for line in text.splitlines() if PIN_RE.match(line.strip())]
    # Guard against an empty or truncated response replacing a good snapshot.
    if len(pins) < 300:
        raise RuntimeError(f"Only {len(pins)} pins in {SOURCE_URL}; refusing to refresh")
    return pins


def split_snapshot(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    header = [line for line in lines if line.startswith("#") or not line.strip()]
    pins = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return "\n".join(header).rstrip("\n"), pins


def describe_changes(old: list[str], new: list[str]) -> list[str]:
    old_map = dict(p.split("==", 1) for p in old)
    new_map = dict(p.split("==", 1) for p in new)
    out = []
    for name in sorted(set(old_map) | set(new_map), key=str.lower):
        before, after = old_map.get(name), new_map.get(name)
        if before != after:
            out.append(f"{name}: {before or '(absent)'} -> {after or '(removed)'}")
    return out


def bootstrapped_notebooks() -> list[Path]:
    """Notebooks that carry a locked install cell and a requirements file.

    Notebooks excluded from CI are left alone: their pins cannot be verified
    after a re-lock, and several are held on an older stack on purpose.
    """
    exclusions = load_exclusions()
    found = []
    for nb_path in sorted(REPO_ROOT.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in nb_path.parts:
            continue
        if is_excluded(str(nb_path.relative_to(REPO_ROOT)), exclusions):
            continue
        try:
            find_install_cell(nbformat.read(nb_path, as_version=4))
            requirements_for(nb_path)
        except Exception:
            continue
        found.append(nb_path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relock", action="store_true",
                        help="Re-lock every bootstrapped notebook when the snapshot changed")
    parser.add_argument("--force-relock", action="store_true",
                        help="Re-lock even when the snapshot did not change")
    args = parser.parse_args()

    header, old_pins = split_snapshot(CONSTRAINT.read_text())
    new_pins = fetch_pins()
    changes = describe_changes(old_pins, new_pins)
    changed = bool(changes)

    if changed:
        today = datetime.date.today().isoformat()
        header = REFRESHED_RE.sub(f"# Last refreshed: {today}", header)
        CONSTRAINT.write_text(header + "\n" + "\n".join(new_pins) + "\n")
        print(f"Refreshed {CONSTRAINT.relative_to(REPO_ROOT)}: {len(changes)} package(s) changed")
        for line in changes:
            print(f"  {line}")
    else:
        print("Snapshot already matches Colab's current pip freeze")

    rc = 0
    if (changed and args.relock) or args.force_relock:
        notebooks = bootstrapped_notebooks()
        print(f"Re-locking {len(notebooks)} notebook(s)")
        rc = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("lock_notebook.py")), *map(str, notebooks)]
        ).returncode

    print(f"changed={'true' if changed else 'false'}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
