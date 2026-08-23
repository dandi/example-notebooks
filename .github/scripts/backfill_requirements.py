"""Derive requirements.in files for notebook groups that predate the contract.

For each image group without a requirements file, collect the top-level
modules its notebooks import, then resolve those to distribution names using
`importlib.metadata.packages_distributions()` inside the group's published
container image (the exact environment the notebook was verified in, so the
mapping is not a guess). Standard-library modules and the group's own helper
files are skipped; `pkg @ git+...` pins from the install cell are direct
dependencies by definition and are carried over verbatim.

Known incompatibilities are encoded as bounds: nwbwidgets only imports on the
pre-2024 stack, so groups that pin it get pynwb<3, hdmf<4, zarr<3.

Usage:
    python .github/scripts/backfill_requirements.py [--dry-run] [--filter REGEX]

Requires docker and nbformat.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import nbformat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_notebook_image import DEFAULT_IMAGE_PREFIX, collect_groups, matches  # noqa: E402
from lock_notebook import requirements_for  # noqa: E402

IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w]*)|import\s+([A-Za-z_][\w]*))", re.M)
NWBWIDGETS_BOUNDS = ["pynwb<3", "hdmf<4", "zarr<3"]
# Import names whose distribution is not discoverable by name matching.
IMPORT_ALIASES = {"skimage": "scikit-image", "cv2": "opencv-python", "PIL": "pillow",
                  "yaml": "pyyaml", "sklearn": "scikit-learn"}

# Runs inside the image: maps import names to distributions, and scans the
# helper modules baked into /work (local .py files, packages, and files the
# install cell fetched with curl) for their own imports, since a notebook's
# direct dependencies include whatever its helpers import.
PROBE = r"""
import importlib.metadata as m, json, re, sys
from pathlib import Path
IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_]\w*)|import\s+([A-Za-z_]\w*))", re.M)
work = Path("/work")
helper_modules, helper_imports = set(), set()
for py in work.rglob("*.py"):
    rel = py.relative_to(work)
    helper_modules.add(rel.parts[0].removesuffix(".py"))
    try:
        for mm in IMPORT_RE.finditer(py.read_text(errors="ignore")):
            helper_imports.add(mm.group(1) or mm.group(2))
    except OSError:
        pass
print(json.dumps({
    "dists": m.packages_distributions(),
    "stdlib": sorted(sys.stdlib_module_names),
    "helper_modules": sorted(helper_modules),
    "helper_imports": sorted(helper_imports),
}))
"""


def notebook_imports(path: Path) -> tuple[set[str], bool]:
    """Top-level imports, plus whether the notebook drives the dandi CLI from shell cells."""
    nb = nbformat.read(path, as_version=4)
    mods: set[str] = set()
    uses_dandi_cli = False
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for line in cell.source.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("!dandi ") or stripped.startswith("!dandi\t"):
                uses_dandi_cli = True
            if stripped.startswith(("!", "%")):
                continue
            for m in IMPORT_RE.finditer(line):
                mods.add(m.group(1) or m.group(2))
    return mods, uses_dandi_cli


def probe_image(image: str) -> dict:
    subprocess.run(["docker", "pull", "-q", image], check=True, capture_output=True)
    r = subprocess.run(["docker", "run", "--rm", "-i", image, "python", "-"],
                       input=PROBE, capture_output=True, text=True, check=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--filter", default="")
    parser.add_argument("--force", action="store_true", help="rewrite existing requirements files too")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    for group in collect_groups():
        if not matches(group, args.filter):
            continue
        nb_paths = [repo / group.directory / n for n in group.notebooks]
        try:
            requirements_for(nb_paths[0])
            if not args.force:
                continue  # already has a requirements file
        except FileNotFoundError:
            pass

        imports: set[str] = set()
        uses_dandi_cli = False
        for p in nb_paths:
            mods, cli = notebook_imports(p)
            imports |= mods
            uses_dandi_cli = uses_dandi_cli or cli

        # Probe this group's image, or a sibling group's in the same directory
        # when this group has never published (same helpers, near-identical env).
        siblings = [g for g in collect_groups() if g.directory == group.directory]
        info = None
        for candidate in [group] + [g for g in siblings if g.name != group.name]:
            try:
                info = probe_image(f"{DEFAULT_IMAGE_PREFIX}/{candidate.name}:latest")
                break
            except subprocess.CalledProcessError:
                continue
        if info is None:
            print(f"[{group.name}] no image to probe in {group.directory}; skipping", file=sys.stderr)
            continue
        dists, stdlib = info["dists"], set(info["stdlib"])
        local_modules = set(info["helper_modules"])
        imports |= set(info["helper_imports"])
        if uses_dandi_cli:
            direct_extra = {"dandi"}
        else:
            direct_extra = set()

        direct: set[str] = set(direct_extra)
        unmapped: list[str] = []
        for mod in sorted(imports):
            if mod in stdlib or mod in local_modules:
                continue
            names = dists.get(mod)
            if names:
                direct.update(names)
                continue
            # Not installed in the probed image (a sibling's): fall back to the
            # group's own pins, by alias or by name with _ and - interchangeable.
            wanted = IMPORT_ALIASES.get(mod, mod).lower().replace("_", "-")
            pinned = [pin.split("==")[0] for pin in group.pins
                      if pin.split("==")[0].lower().replace("_", "-") == wanted]
            if pinned:
                direct.add(pinned[0])
            else:
                unmapped.append(mod)

        # NWB extension packages are used through a file's cached schema and
        # never imported, so the import scan cannot see them; they are only
        # ever installed deliberately, so carry them over from the old lock.
        for pin in group.pins:
            name = pin.split("==")[0].split(" @ ")[0].strip()
            if name.lower().startswith("ndx-") and " @ " not in pin:
                direct.add(name)

        git_pins = [p for p in group.pins if " @ " in p]
        for gp in git_pins:
            name = gp.split(" @ ")[0].strip()
            direct.discard(name)
        lines = sorted(direct, key=str.lower) + git_pins
        if any(p.startswith("nwbwidgets==") for p in group.pins):
            lines += NWBWIDGETS_BOUNDS
        elif "pynwb" in direct or "hdmf" in direct:
            # Hold the NWB stack at the majors the fleet was last verified on;
            # a Colab-driven re-lock should not double as a pynwb major upgrade.
            lines += ["pynwb<4", "hdmf<5"]

        # One requirements.in per directory when the directory holds a single
        # group; otherwise a per-notebook file, keyed on the first notebook.
        if len(siblings) == 1:
            target = repo / group.directory / "requirements.in"
        else:
            target = nb_paths[0].with_name(f"{nb_paths[0].stem}.requirements.in")

        rel = target.relative_to(repo)
        print(f"[{group.name}] -> {rel}: {', '.join(lines)}"
              + (f"  (UNMAPPED imports: {', '.join(unmapped)})" if unmapped else ""))
        if not args.dry_run:
            target.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
