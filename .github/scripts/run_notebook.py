"""Run one Colab-bootstrap notebook end-to-end in a fresh-ish env.

Used by CI to verify that the install cell's pinned deps actually install on
Python 3.12 / linux x86_64, that any colocated helper `.py` files fetched via
`!curl` resolve, and that the notebook executes without an unhandled exception.

The Jupyter ZMQ kernel can be flaky in CI sandboxes, so we sidestep it: extract
the pinned deps from the install cell, install them with `uv pip install
--system`, stub out the install cell itself, convert the notebook to a `.py`
script with `nbconvert --to script`, and run that script under `ipython`
(which handles `!shell` magic without needing a kernel).

Exit code 0 on pass, 1 on any failure (install, helper fetch, or notebook
execution). Writes a `result.json` next to the executed script with detailed
status that the workflow can surface in a summary.

Usage:
    python run_notebook.py <notebook-path> --output-dir <dir>

Assumes `uv` and `nbformat` are already on PATH / importable.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import nbformat


def slugify(path: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_")


def find_install_cell(nb):
    for i, cell in enumerate(nb.cells[:8]):
        if cell.cell_type != "code":
            continue
        if "uv pip install --system" not in cell.source:
            continue
        pins = re.findall(r'"([^"]+)"', cell.source)
        helpers = [
            line.strip()
            for line in cell.source.splitlines()
            if line.strip().startswith(("!curl", "!wget"))
        ]
        return pins, helpers, i
    raise RuntimeError(
        "Missing Colab-bootstrap install cell. "
        "CI walks every notebook in the repo and expects each one to begin with a "
        "code cell containing `!uv pip install --system \"pkg==ver\" ...` so that "
        "its dep set is fully pinned and reproducible. "
        "To fix: add the bootstrap cells (see PR #149 for the pattern) — OR, if "
        "the notebook genuinely can't be tested headlessly (needs a database, "
        "proprietary creds, etc), add its path to `.github/notebook-test-exclusions.txt` "
        "with a comment explaining why."
    )


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook")
    parser.add_argument("--output-dir", default="/tmp/notebook-test")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args()

    nb_path = Path(args.notebook)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.notebook)

    result_path = out_dir / f"{slug}.result.json"
    log_path = out_dir / f"{slug}.log"
    script_path = out_dir / f"{slug}.py"

    status = {"notebook": args.notebook, "stage": "start", "duration_s": 0}
    t0 = time.time()

    def finalize(stage: str, ok: bool, error: str | None = None, **extra) -> int:
        status["stage"] = stage
        status["ok"] = ok
        status["duration_s"] = round(time.time() - t0, 1)
        if error:
            status["error"] = error[-4000:]
        status.update(extra)
        result_path.write_text(json.dumps(status, indent=2))
        print(json.dumps(status, indent=2))
        return 0 if ok else 1

    nb = nbformat.read(nb_path, as_version=4)
    try:
        pins, helpers, install_idx = find_install_cell(nb)
        status["n_pins"] = len(pins)
        status["n_helpers"] = len(helpers)
    except Exception as e:
        return finalize("extract", False, error=str(e))

    log_path.write_text("")

    r = run(
        ["uv", "pip", "install", "--system",
         "ipython", "nbconvert", "nbformat", *pins]
    )
    with log_path.open("a") as f:
        f.write(f"=== install rc={r.returncode} ===\n")
        f.write(f"--- stdout ---\n{r.stdout[-2000:]}\n")
        f.write(f"--- stderr ---\n{r.stderr[-3000:]}\n")
    if r.returncode != 0:
        return finalize("install", False, error=r.stderr[-3000:])

    nb_dir = nb_path.parent
    for h in helpers:
        cmd_str = h.lstrip("!").strip()
        m = re.search(r"-o\s+(\S+)", cmd_str)
        if m:
            target = nb_dir / m.group(1)
            target.parent.mkdir(parents=True, exist_ok=True)
        r = run(["bash", "-c", cmd_str], cwd=str(nb_dir))
        with log_path.open("a") as f:
            f.write(f"\n=== helper rc={r.returncode}: {cmd_str[:120]} ===\n")
            f.write(f"{r.stderr[-500:]}\n")
        if r.returncode != 0:
            return finalize("helper", False,
                            error=f"helper failed: {cmd_str[:200]}\n{r.stderr[-1000:]}")

    nb_for_exec = copy.deepcopy(nb)
    nb_for_exec.cells[install_idx].source = (
        "# install cell skipped during CI (deps preinstalled into system Python)"
    )
    tmp_nb = out_dir / f"{slug}.toexec.ipynb"
    nbformat.write(nb_for_exec, str(tmp_nb))

    r = run(["jupyter", "nbconvert", "--to", "script", "--stdout", str(tmp_nb)])
    if r.returncode != 0:
        return finalize("convert", False, error=r.stderr[-3000:])
    raw_script = r.stdout

    # Insert progress markers before each `# In[...]` cell separator so the
    # CI log shows which cell is running. If the process is killed mid-cell
    # (eg OOM), the last marker tells you the offending cell.
    instrumented = []
    for line in raw_script.splitlines(keepends=True):
        m = re.match(r"# In\[(.*?)\]:", line.strip())
        if m:
            cell_label = m.group(1) or "?"
            instrumented.append(
                f'import sys as _sys; print("::cell {cell_label}::", flush=True); _sys.stderr.flush()\n'
            )
        instrumented.append(line)
    script_path.write_text("".join(instrumented))

    # Stream ipython output live to this process's stdout/stderr so CI logs
    # show progress in real time. Tee a copy to the log file via Popen.
    import shlex
    cmd = ["ipython", "--colors=NoColor", "--no-banner",
           "--InteractiveShell.history_load_length=0", str(script_path)]
    print(f"\n=== executing notebook (streaming) ===\n  {shlex.join(cmd)}", flush=True)
    log_f = log_path.open("a")
    log_f.write(f"\n=== execute (streaming) ===\n")
    log_f.flush()
    proc = subprocess.Popen(
        cmd, cwd=str(nb_dir),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    captured = []
    try:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log_f.write(line)
            captured.append(line)
        proc.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        log_f.close()
        return finalize("execute", False,
                        error=f"hit overall {args.timeout}s timeout")
    log_f.close()

    full_output = "".join(captured)
    looks_failed = (
        proc.returncode != 0
        or "Traceback (most recent call last)" in full_output
    )
    if looks_failed:
        return finalize("execute", False, error=full_output[-3000:])

    return finalize("done", True)


if __name__ == "__main__":
    sys.exit(main())
