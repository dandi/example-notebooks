"""Publish an executed notebook to the PR preview and refresh the PR checklist.

Called by deploy-executed-notebooks.yml (dispatched by each matrix job of
test-changed-notebooks.yml as its notebook finishes) and by that workflow's
finalize job:

    pr_preview.py comment --pr N --run-id R --notebooks notebooks.json

Rebuilds the sticky "Executed notebooks" comment from the artifacts the test
run has uploaded so far. A job uploads `executed-<slug>-pass`, `-fail` or
`-none` before the deploy is requested, so the comment is a pure function of
run state: concurrent rebuilds can reorder but never lose a result, and the
final rebuild after the matrix completes is exact.

Requires `gh` authenticated with pull-requests:write and actions:read.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_notebook import slugify  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "dandi/example-notebooks")
PREVIEW_BASE = "https://notebooks.dandiarchive.org/pr-preview/{pr}/notebooks"
# Same marker marocchino/sticky-pull-request-comment used before, so the
# comment on PRs opened under the old workflow is updated rather than duplicated.
COMMENT_MARKER = "<!-- Sticky Pull Request Commentexecuted-notebooks -->"


def gh_api(*args: str, input_json: dict | None = None) -> subprocess.CompletedProcess:
    cmd = ["gh", "api", *args]
    if input_json is not None:
        cmd += ["--input", "-"]
    return subprocess.run(cmd, capture_output=True, text=True,
                          input=json.dumps(input_json) if input_json is not None else None)


def run_artifacts(run_id: str) -> set[str]:
    r = gh_api(f"repos/{REPO}/actions/runs/{run_id}/artifacts", "--paginate",
               "-q", ".artifacts[].name")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return set(r.stdout.split())


def build_comment(pr: int, run_id: str, notebooks: list[str], head_sha: str) -> tuple[str, bool]:
    artifacts = run_artifacts(run_id)
    base = PREVIEW_BASE.format(pr=pr)
    lines = ["## Executed notebooks", "",
             "CI executes the notebooks changed in this PR through a Jupyter kernel "
             "and publishes each one, with its outputs, as soon as it finishes. "
             "Links appear below as notebooks complete; an hourglass means the "
             "notebook is still running.", ""]
    n_done = 0
    for nb in notebooks:
        slug = slugify(nb)
        if f"executed-{slug}-pass" in artifacts:
            mark, n_done = "✅", n_done + 1
        elif f"executed-{slug}-fail" in artifacts:
            mark, n_done = "❌", n_done + 1
        elif f"executed-{slug}-none" in artifacts:
            # The run never produced an executed copy (install failed, etc).
            lines.append(f"- ❌ `{nb}` (no executed copy; see the job log)")
            n_done += 1
            continue
        else:
            lines.append(f"- ⏳ `{nb}`")
            continue
        lines.append(f"- {mark} [`{nb}`]({base}/{slug}.html)")
    complete = n_done == len(notebooks)
    lines += ["", f"_{n_done} of {len(notebooks)} finished. Commit `{head_sha}`. "
              "The executed copies live only in the preview and are removed when the "
              "PR closes; nothing is committed to the branch._", "", COMMENT_MARKER]
    return "\n".join(lines) + "\n", complete


def upsert_comment(pr: int, body: str) -> None:
    r = gh_api(f"repos/{REPO}/issues/{pr}/comments", "--paginate",
               "-q", f'.[] | select(.body | contains("{COMMENT_MARKER}")) | .id')
    ids = r.stdout.split()
    if ids:
        gh_api("-X", "PATCH", f"repos/{REPO}/issues/comments/{ids[0]}", input_json={"body": body})
    else:
        gh_api("-X", "POST", f"repos/{REPO}/issues/{pr}/comments", input_json={"body": body})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("comment")
    c.add_argument("--pr", type=int, required=True)
    c.add_argument("--run-id", required=True)
    c.add_argument("--notebooks", type=Path, required=True, help="JSON list of notebook paths")
    c.add_argument("--head-sha", default="")
    args = parser.parse_args()

    notebooks = json.loads(args.notebooks.read_text())
    body, complete = build_comment(args.pr, args.run_id, notebooks, args.head_sha[:7])
    print(body)
    upsert_comment(args.pr, body)
    print("complete" if complete else "partial")
    return 0


if __name__ == "__main__":
    sys.exit(main())
