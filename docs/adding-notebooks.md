# Adding a notebook: CI, Colab, and the exclusion lists

This guide explains what happens to a notebook after you open a Pull Request —
how it is tested, how it is made runnable in Google Colab, and the three
`.github/*.txt` lists that control that behavior. For the basic file layout and
`environment.yml`, see the [README](../README.md#submission-instructions);
this doc picks up where that leaves off.

## TL;DR — checklist for a new notebook

- [ ] Place it under `<dandiset id>/<org or lab>/<mnemonic>/` with a `README.md`
      and `environment.yml` (see main README).
- [ ] Prepend the **Colab-bootstrap cells** (badge → install intro → pinned
      install cell → restart admonition). See [below](#the-colab-bootstrap-cells).
- [ ] Generate the install cell's pins with `uv pip compile`, constrained to
      Colab's versions. See [generating the install cell](#generating-the-install-cell).
- [ ] Make sure it runs **headlessly** — no `fig.show()` on a default plotly
      renderer, no `cv2.imshow`, no `%matplotlib widget`, no `input()`. See
      [headless gotchas](#headless-gotchas).
- [ ] Open the PR. CI runs the changed notebook end-to-end. Green = good.
- [ ] If it genuinely can't run in CI (or shouldn't get a Colab button), add it
      to the right [exclusion list](#the-three-github-lists) with a one-line reason.

## How CI tests a notebook

Two workflows execute notebooks:

| Workflow | Trigger | Scope |
|---|---|---|
| [`test-changed-notebooks.yml`](../.github/workflows/test-changed-notebooks.yml) | PR touching `**.ipynb` (or the test harness) | Only the notebooks **added/modified** in the PR |
| [`test-all-notebooks-weekly.yml`](../.github/workflows/test-all-notebooks-weekly.yml) | Mondays 06:00 UTC + manual dispatch | Every testable notebook; opens an issue on failure |

Both call [`.github/scripts/run_notebook.py`](../.github/scripts/run_notebook.py)
on an `ubuntu-latest` runner with Python 3.12. That script:

1. Finds the **install cell** (the first code cell containing
   `!uv pip install --system`) and extracts the pinned package list from it.
2. Installs those exact pins with `uv pip install --system`.
3. Runs any `!curl`/`!wget` helper-file fetches from that cell.
4. **Stubs out** the install cell, converts the notebook to a script with
   `nbconvert --to script`, and runs it under `ipython` (sidestepping the
   flaky ZMQ kernel).
5. Exits non-zero — failing CI — on any install error, helper-fetch failure, or
   notebook exception.

> **Key consequence:** CI is a *fresh-env* test. It installs **only** what the
> install cell pins — there is no preinstalled safety net. If the notebook
> imports something the install cell doesn't pin, CI fails (even if it "works on
> Colab," where that package happens to be preinstalled).

`test-changed-notebooks.yml` only tests notebooks **changed in the PR**. A
notebook already on `master` that would fail today is not re-run until it is
touched again (or until the weekly sweep catches it). Don't assume "it's on
master, so it's green."

A brand-new notebook **without** an install cell fails by design — CI can't
know what to install. Add the bootstrap, or add the notebook to an exclusion
list with a reason.

## The Colab bootstrap cells

Every testable notebook begins with four cells (the pattern established in
[PR #149](https://github.com/dandi/example-notebooks/pull/149)):

1. **Colab badge** (markdown):
   ```markdown
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dandi/example-notebooks/blob/master/<path-to-notebook>.ipynb)
   ```
2. **Install intro** (markdown): one paragraph explaining the install cell.
3. **Install cell** (code) — the one CI keys off:
   ```python
   #@title Installing requirements (click ▶ to run) { display-mode: "form" }
   # Colab provides Python 3.12. We install with `uv --system` because Colab's
   # kernel runs outside a virtualenv. All versions (direct + transitive) are
   # pinned below so the notebook is reproducible regardless of resolver drift.
   !pip install -q uv
   !uv pip install --system \
       "package-a==1.2.3" \
       "package-b==4.5.6" \
       ...
   ```
   The `{ display-mode: "form" }` collapses the cell to a one-line bar in Colab
   so users aren't faced with ~100 lines of pins. If the notebook needs a
   colocated helper `.py`, fetch it at the end of this cell:
   `!curl -sL -o helper.py https://raw.githubusercontent.com/dandi/example-notebooks/master/<path>/helper.py`
4. **Restart admonition** (markdown): tells the user to restart the runtime
   after install, because upgrading C-extension packages mid-session requires it.

### Why fully pinned?

Pinning **all** transitive deps (not just direct ones) makes the notebook
reproducible forever — it can't break later when an upstream release changes a
default. It's also what CI installs, so a green CI run means the exact pinned
set works on Python 3.12 / linux.

## Generating the install cell

Resolve a full, pinned lock with [`uv`](https://github.com/astral-sh/uv),
constrained to **Colab's preinstalled versions** so the install is a no-op for
packages Colab already ships (faster, and avoids the "RESTART RUNTIME" prompt
that changing `numpy` and other C-extensions triggers):

```bash
uv pip compile requirements.in \
    --python-version 3.12 \
    --python-platform linux \
    --constraint .github/colab-preinstalled.txt \
    -o pins.txt
```

where `requirements.in` lists the notebook's **direct** imports (e.g. `dandi`,
`pynwb`, `remfile`, `matplotlib`, `pandas`). Then format each `pkg==ver` line
into the `!uv pip install --system \` block.

[`.github/colab-preinstalled.txt`](../.github/colab-preinstalled.txt) is a
pip-freeze of the current Colab Python 3.12 runtime (numpy 2.0.2, etc.). Using
it as a constraint keeps your pins aligned with Colab. When a notebook's needs
are genuinely incompatible with a Colab version, the resolver falls back to a
non-Colab version for that package — the user will then get a restart prompt,
which is the correct trade-off.

> **nbformat gotcha:** cell `id` fields require `nbformat_minor >= 5`. If you
> prepend cells and validation complains about an unexpected `id`, bump the
> notebook's `nbformat_minor` to 5.

## Headless gotchas

CI runs notebooks with **no display and no browser**. Most plotting is fine;
a few patterns are not. Before opening a PR, make sure none of these slip in:

| Pattern | Headless? | Notes |
|---|---|---|
| `plt.show()` (matplotlib) | ✅ fine | Falls back to the Agg backend. |
| `IPython.display.IFrame(...)` | ✅ fine | Produces an inert HTML repr; never fetches or opens anything. |
| `fig.show()` (**plotly**) | ❌ **fails** | Default renderer is `"browser"` → calls `webbrowser.open()` → `Error: could not locate runnable browser`. Set a notebook renderer once near the top: `import plotly.io as pio; pio.renderers.default = "iframe"` (renders in Colab, safe headless). |
| `cv2.imshow` / `cv2.namedWindow` | ❌ fails | Needs a GUI window. |
| `%matplotlib notebook` / `widget` / `tk` / `qt` | ❌ fails | Interactive backends need a frontend. Use `%matplotlib inline`. |
| `input()` / `getpass()` | ❌ hangs | No stdin in CI. |
| `webbrowser.open(...)` | ❌ fails | No browser on the runner. |

The plotly case is the most common surprise: a notebook works in Colab (which
has a notebook renderer + preinstalled plotly) but fails in CI. The fix is the
one-line `pio.renderers.default` setting above — keep it in CI **and** Colab.

## The three `.github` lists

These three files control different things and are **independent** of each
other. Add a notebook to whichever applies, always with a one-line reason.

### `colab-preinstalled.txt`
[`.github/colab-preinstalled.txt`](../.github/colab-preinstalled.txt) — **not**
an exclusion list. It's a snapshot of Colab's preinstalled package versions,
used as the `uv pip compile --constraint` when generating install-cell pins (see
[above](#generating-the-install-cell)). Refresh it when Colab bumps its runtime.

### `notebook-test-exclusions.txt` → "skip in CI"
[`.github/notebook-test-exclusions.txt`](../.github/notebook-test-exclusions.txt)
— notebooks the CI test sweep should skip. Add a notebook here when it can't run
cleanly on a headless CI runner: needs a database/credentials, hits a
headless-incompatible API the slim runner image lacks, a pre-existing content
bug, or an upstream break not yet fixed. Lines are fnmatch globs relative to the
repo root. Removing the line re-enables testing once the issue is fixed.

### `notebook-colab-exclusions.txt` → "no Colab button"
[`.github/notebook-colab-exclusions.txt`](../.github/notebook-colab-exclusions.txt)
— notebooks that should **not** show an "Open in Colab" button on the index
page (consumed by `collect_and_render.py`). Add a notebook here when clicking
"Open in Colab" would give a broken experience even on a fresh Colab runtime:
stale data paths, missing creds, removed upstream APIs, wheels lacking a needed
feature, or runtimes too long for a tutorial.

### They are independent

A notebook can be on one list but not the other:

- **Test-excluded but Colab-OK:** `read_avi.ipynb` uses OpenCV's `libxcb`, which
  the slim CI image lacks but Colab has → on test-exclusions, **not** on
  colab-exclusions.
- **Colab-excluded but test-OK:** rare, but e.g. a notebook that runs in CI yet
  points users at data they can't access interactively.
- **Both:** the DataJoint examples need a MySQL server that neither CI nor Colab
  provides → on both lists.

## Where to get help

Reach out on the [DANDI helpdesk](https://github.com/dandi/helpdesk/issues/new/choose).
