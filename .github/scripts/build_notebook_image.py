"""Group notebooks into container-image build units and prepare build contexts.

Notebooks that carry the Colab-bootstrap install cell are grouped by
(directory, pin-set): notebooks in the same directory whose install cells pin
the identical dependency set share one image. The image for a group contains
every file of that directory (minus notebooks belonging to other groups) plus
any helper files the install cells fetch via `!curl`/`!wget`, with the pinned
dependencies preinstalled into the system Python.

Subcommands:
    list-groups [--filter REGEX] [--names-only]
        Print the groups as JSON. `--names-only` emits just the group names,
        suitable for a GitHub Actions matrix.
    prepare --name NAME --context-dir DIR [--image-prefix PREFIX]
        Write a docker build context (requirements.txt + work/) for one group
        and emit image name, build hash, default notebook, and the notebook
        list to $GITHUB_OUTPUT (or stdout when unset).

The pin extraction reuses `find_install_cell` from run_notebook.py, so the
image contents stay in lockstep with what CI tests. Entries captured by that
regex that are not actual pins (it also picks up the literal `form` from the
`{ display-mode: "form" }` title line) are filtered out: only `pkg==ver` and
`pkg @ url` requirements are baked into an image.

Assumes `nbformat` is importable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import nbformat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from list_notebooks import REPO_ROOT, is_excluded, load_exclusions  # noqa: E402
from run_notebook import find_install_cell  # noqa: E402

DOCKERFILE = REPO_ROOT / ".github" / "docker" / "Dockerfile"
DEFAULT_IMAGE_PREFIX = "ghcr.io/dandi/example-notebooks"
IMAGE_INCLUSIONS = REPO_ROOT / ".github" / "notebook-image-inclusions.txt"


def load_image_inclusions() -> list[str]:
    """Patterns for notebooks that are CI-test-excluded but image-runnable.

    The container image ships system libraries the slim CI runner lacks, so
    the image pipeline rescues these from the shared test-exclusion list.
    """
    if not IMAGE_INCLUSIONS.exists():
        return []
    return [
        line.strip()
        for line in IMAGE_INCLUSIONS.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def real_pins(pins: list[str]) -> tuple[list[str], list[str]]:
    """Split install-cell entries into actual requirements and strays."""
    kept = [p for p in pins if "==" in p or " @ " in p]
    dropped = [p for p in pins if p not in kept]
    return kept, dropped


@dataclass
class Group:
    directory: str  # repo-relative, e.g. "001550/PaganLab"
    pin_hash: str
    pins: list[str]
    helpers: list[str] = field(default_factory=list)
    notebooks: list[str] = field(default_factory=list)  # filenames within directory
    name: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "directory": self.directory,
            "pin_hash": self.pin_hash,
            "notebooks": sorted(self.notebooks),
        }


def collect_groups() -> list[Group]:
    exclusions = load_exclusions()
    inclusions = load_image_inclusions()
    groups: dict[tuple[str, str], Group] = {}
    for path in sorted(REPO_ROOT.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in path.parts:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        if is_excluded(rel, exclusions) and not is_excluded(rel, inclusions):
            continue
        nb = nbformat.read(path, as_version=4)
        try:
            pins, helpers, _ = find_install_cell(nb)
        except RuntimeError:
            continue  # no Colab bootstrap -> no image
        kept, _ = real_pins(pins)
        pin_hash = hashlib.sha256("\n".join(sorted(kept)).encode()).hexdigest()
        directory = str(path.parent.relative_to(REPO_ROOT))
        key = (directory, pin_hash)
        group = groups.setdefault(
            key, Group(directory=directory, pin_hash=pin_hash, pins=sorted(kept))
        )
        group.notebooks.append(path.name)
        for h in helpers:
            if h not in group.helpers:
                group.helpers.append(h)

    per_dir: dict[str, list[Group]] = {}
    for g in groups.values():
        per_dir.setdefault(g.directory, []).append(g)
    for dir_groups in per_dir.values():
        for g in dir_groups:
            g.name = slug(g.directory)
            if len(dir_groups) > 1:
                g.name += "-" + slug(Path(sorted(g.notebooks)[0]).stem)

    result = sorted(groups.values(), key=lambda g: g.name)
    names = [g.name for g in result]
    assert len(names) == len(set(names)), f"group name collision: {names}"
    return result


def matches(group: Group, pattern: str) -> bool:
    if not pattern:
        return True
    rx = re.compile(pattern)
    return bool(
        rx.search(group.directory)
        or any(rx.search(f"{group.directory}/{n}") for n in group.notebooks)
    )


INFRA_PREFIXES = (
    ".github/docker/",
    ".github/scripts/build_notebook_image.py",
    ".github/scripts/run_notebook.py",
    ".github/workflows/build-notebook-images.yml",
    ".github/notebook-test-exclusions.txt",
    ".github/notebook-image-inclusions.txt",
)


def groups_for_changed_files(groups: list[Group], changed: list[str]) -> list[Group]:
    """Groups affected by a set of changed repo paths.

    A change to the image tooling affects every group; otherwise a group is
    affected when any changed path lies inside its directory.
    """
    if any(p.startswith(INFRA_PREFIXES) for p in changed):
        return groups
    return [
        g for g in groups
        if any(p == g.directory or p.startswith(g.directory + "/") for p in changed)
    ]


def cmd_list_groups(args: argparse.Namespace) -> int:
    groups = [g for g in collect_groups() if matches(g, args.filter)]
    if args.changed_only:
        changed = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
        groups = groups_for_changed_files(groups, changed)
    if args.names_only:
        print(json.dumps([g.name for g in groups]))
    else:
        print(json.dumps([g.as_dict() for g in groups], indent=2))
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    groups = [g for g in collect_groups() if g.name == args.name]
    if not groups:
        print(f"error: no group named {args.name!r}", file=sys.stderr)
        return 1
    group = groups[0]

    context = Path(args.context_dir)
    if context.exists():
        shutil.rmtree(context)
    work = context / "work"

    group_notebooks = set(group.notebooks)
    src_dir = REPO_ROOT / group.directory

    def ignore(directory: str, names: list[str]) -> list[str]:
        ignored = [n for n in names if n == ".ipynb_checkpoints"]
        for n in names:
            if not n.endswith(".ipynb"):
                continue
            in_group = (
                Path(directory) == src_dir and n in group_notebooks
            )
            if not in_group:
                ignored.append(n)
        return ignored

    shutil.copytree(src_dir, work, ignore=ignore)

    (context / "requirements.txt").write_text("\n".join(group.pins) + "\n")

    # Bake helper files the same way run_notebook.py fetches them in CI.
    for h in group.helpers:
        cmd_str = h.lstrip("!").strip()
        m = re.search(r"-o\s+(\S+)", cmd_str)
        if m:
            target = work / m.group(1)
            target.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["bash", "-c", cmd_str], cwd=str(work), capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"error: helper failed: {cmd_str}\n{r.stderr[-1000:]}", file=sys.stderr)
            return 1

    h = hashlib.sha256()
    for pin in group.pins:
        h.update(pin.encode() + b"\n")
    for helper in group.helpers:
        h.update(helper.encode() + b"\n")
    for name in sorted(group.notebooks):
        h.update((REPO_ROOT / group.directory / name).read_bytes())
    h.update(DOCKERFILE.read_bytes())
    build_hash = h.hexdigest()

    notebooks = sorted(group.notebooks)
    outputs = {
        "image": f"{args.image_prefix}/{group.name}",
        "build_hash": build_hash,
        "build_hash_short": build_hash[:12],
        "default_notebook": notebooks[0],
        "notebooks": json.dumps(notebooks),
        "context_dir": str(context),
    }
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            for k, v in outputs.items():
                f.write(f"{k}={v}\n")
    print(json.dumps(outputs, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-groups")
    p_list.add_argument("--filter", default="", help="regex on directory or notebook path")
    p_list.add_argument("--names-only", action="store_true")
    p_list.add_argument(
        "--changed-only", action="store_true",
        help="read newline-separated changed repo paths from stdin and keep only "
             "affected groups (any image-tooling change selects all groups)",
    )
    p_list.set_defaults(func=cmd_list_groups)

    p_prep = sub.add_parser("prepare")
    p_prep.add_argument("--name", required=True)
    p_prep.add_argument("--context-dir", required=True)
    p_prep.add_argument("--image-prefix", default=DEFAULT_IMAGE_PREFIX)
    p_prep.set_defaults(func=cmd_prepare)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
