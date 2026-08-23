"""Generate or refresh a notebook's Colab-bootstrap cells from a requirements.in.

Contributors commit a `requirements.in` next to their notebook listing only the
notebook's direct dependencies (e.g. `pynwb`, `remfile`, `matplotlib`). This
script compiles that into a fully pinned set with `uv pip compile`, constrained
to Colab's preinstalled versions, and writes the four bootstrap cells (badge,
install intro, pinned install cell, restart admonition) into the notebook —
prepending them when absent, or refreshing the install cell's pin block in
place (helper `!curl`/`!wget` lines are preserved) when already present.

The requirements file is resolved per notebook: `<stem>.requirements.in` next
to the notebook wins when present, otherwise the directory's `requirements.in`
is used. One `requirements.in` shared by all notebooks in a directory keeps
their pin sets identical, so they are tested against one environment and are
published together in one container image (see ../docker/README.md).

Usage:
    python .github/scripts/lock_notebook.py <notebook.ipynb> [...]

Assumes `uv` is on PATH and `nbformat` is importable.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
import sys
from pathlib import Path

import nbformat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from list_notebooks import REPO_ROOT  # noqa: E402
from run_notebook import find_install_cell  # noqa: E402

CONSTRAINT = REPO_ROOT / ".github" / "colab-preinstalled.txt"

BADGE = (
    "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
    "(https://colab.research.google.com/github/dandi/example-notebooks/blob/master/{path})"
)
INTRO = (
    "## Installing requirements\n"
    "\n"
    "The cell below installs every Python package needed to run this notebook, "
    "at fully pinned versions, using [`uv`](https://github.com/astral-sh/uv) for "
    "fast resolution. In Colab the cell is collapsed by default — click the "
    "▶ button to run it."
)
RESTART = (
    "> **⚠️ Restart runtime after install**\n"
    ">\n"
    "> The install may upgrade packages already loaded in the kernel. Go to "
    "**Runtime → Restart session**, then **Run all cells below** (skip this "
    "install cell on re-run)."
)
INSTALL_HEADER = (
    '#@title Installing requirements (click ▶ to run) { display-mode: "form" }\n'
    "# Colab provides Python 3.13. We install with `uv --system` because Colab's\n"
    "# kernel runs outside a virtualenv. All versions (direct + transitive) are\n"
    "# pinned below so the notebook is reproducible regardless of resolver drift.\n"
    "!pip install -q uv\n"
)


def requirements_for(nb_path: Path) -> Path:
    per_notebook = nb_path.with_name(f"{nb_path.stem}.requirements.in")
    if per_notebook.exists():
        return per_notebook
    shared = nb_path.parent / "requirements.in"
    if shared.exists():
        return shared
    raise FileNotFoundError(
        f"No requirements file for {nb_path}: expected {per_notebook.name} or "
        f"requirements.in in {nb_path.parent}/. List the notebook's direct "
        "dependencies there (one per line), then re-run this script."
    )


OVERRIDE_PREFIX = "# override:"


def overrides_in(requirements: Path) -> list[str]:
    """Constraint overrides declared as `# override: <spec>` lines.

    Colab's preinstalled versions are applied as constraints so installs stay
    fast and compatible with the runtime. Occasionally a notebook's verified
    stack needs an older version of one of those packages (e.g. the dandi
    release that still reads a file needs click<8.2); an override line replaces
    the Colab pin for that package alone, at the cost of Colab downgrading
    it in the install cell.
    """
    return [
        line[len(OVERRIDE_PREFIX):].strip()
        for line in requirements.read_text().splitlines()
        if line.strip().startswith(OVERRIDE_PREFIX) and line[len(OVERRIDE_PREFIX):].strip()
    ]


def compile_pins(requirements: Path) -> list[str]:
    overrides = overrides_in(requirements)
    constraint = CONSTRAINT
    if overrides:
        # Replace the Colab pin for each overridden package with the override.
        overridden = {re.split(r"[<>=!~\s\[]", spec, 1)[0].lower().replace("_", "-")
                      for spec in overrides}
        kept = [line for line in CONSTRAINT.read_text().splitlines()
                if line.strip() and not line.startswith("#")
                and re.split(r"[<>=!~\s\[]", line.strip(), 1)[0].lower().replace("_", "-")
                not in overridden]
        with tempfile.NamedTemporaryFile("w", suffix=".constraints.txt", delete=False) as f:
            f.write("\n".join(kept + overrides) + "\n")
            constraint = Path(f.name)
    cmd = [
        "uv", "pip", "compile", str(requirements),
        "--python-version", "3.13",
        "--python-platform", "linux",
        "--constraint", str(constraint),
        "--no-header", "--no-annotate",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    finally:
        if constraint is not CONSTRAINT:
            constraint.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(f"uv pip compile failed for {requirements}:\n{r.stderr}")
    pins = [
        line.strip()
        for line in r.stdout.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not pins:
        raise RuntimeError(f"uv pip compile produced no pins from {requirements}")
    return pins


def install_cell_source(pins: list[str], helpers: list[str]) -> str:
    lines = [INSTALL_HEADER + "!uv pip install --system \\"]
    lines += [f'    "{pin}" \\' for pin in pins[:-1]]
    lines.append(f'    "{pins[-1]}"')
    lines += helpers
    return "\n".join(lines)


def lock(nb_path: Path) -> None:
    requirements = requirements_for(nb_path)
    pins = compile_pins(requirements)
    nb = nbformat.read(nb_path, as_version=4)

    try:
        _, helpers, install_idx = find_install_cell(nb)
    except RuntimeError:
        helpers, install_idx = [], None

    if install_idx is not None:
        nb.cells[install_idx].source = install_cell_source(pins, helpers)
        nb.cells[install_idx].metadata["cellView"] = "form"
        action = "refreshed install cell in"
    else:
        rel = nb_path.resolve().relative_to(REPO_ROOT)
        install_cell = nbformat.v4.new_code_cell(install_cell_source(pins, helpers))
        install_cell.metadata["cellView"] = "form"
        nb.cells = [
            nbformat.v4.new_markdown_cell(BADGE.format(path=str(rel).replace(" ", "%20"))),
            nbformat.v4.new_markdown_cell(INTRO),
            install_cell,
            nbformat.v4.new_markdown_cell(RESTART),
        ] + nb.cells
        # Cell ids require nbformat 4.5; prepended cells carry ids.
        nb.nbformat_minor = max(nb.nbformat_minor, 5)
        action = "prepended bootstrap cells to"

    nbformat.validate(nb)
    nbformat.write(nb, nb_path)
    print(f"{action} {nb_path} ({len(pins)} pins from {requirements.name}"
          + (f", kept {len(helpers)} helper line(s)" if helpers else "") + ")")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="+", type=Path)
    args = parser.parse_args()
    failures = 0
    for nb_path in args.notebooks:
        try:
            lock(nb_path)
        except Exception as e:
            print(f"error: {nb_path}: {e}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
