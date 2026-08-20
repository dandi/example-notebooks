# Containerized Notebook Environments

Each Colab-ready notebook in this repository is also published as a
self-contained container image on the GitHub Container Registry. The image
bundles the notebook, any helper files it fetches, a JupyterLab server, and
the exact pinned dependency set from the notebook's install cell,
preinstalled. Unlike the Colab path, the image does not depend on Colab's
current Python version or on PyPI still serving the pinned packages, so it
remains runnable long after the hosted environments have moved on.

## Running a Notebook Image

```
docker run --rm -p 127.0.0.1:8888:8888 ghcr.io/dandi/example-notebooks/001550-paganlab:latest
```

Then open the `http://127.0.0.1:8888/lab?token=...` URL printed in the
terminal. If you already have a Jupyter server running on port 8888 (common),
Docker will refuse to start with an "address already in use" error; pick
another host port, e.g. `-p 127.0.0.1:8890:8888`, and open
`http://127.0.0.1:8890/lab?token=...` instead. The explicit `127.0.0.1:` in
the port mapping matters: it keeps the server off your network interfaces,
and it makes a port collision fail loudly instead of silently routing your
browser to the other Jupyter server. JupyterLab opens on the notebook with its dependencies already
installed; the install cell at the top is a no-op and can be skipped. The
notebooks stream data from the DANDI Archive, so network access is still
required at run time.

Images are multi-arch (`linux/amd64` and `linux/arm64`), so Apple Silicon
machines run them natively rather than under emulation. Emulated execution is
not just slow: Rosetta can deadlock on subprocess spawns inside the kernel,
which shows up as cells hanging forever. If you previously pulled an
amd64-only version of an image, run `docker pull` again to pick up the
multi-arch manifest.

Images are named after the notebook directory (lowercased, with `/` replaced
by `-`). When notebooks in the same directory pin different dependency sets,
the notebook name is appended, e.g.
`ghcr.io/dandi/example-notebooks/000971-lernerlab-seiler-2024-optogenetics-example-notebook`.

## Tags

| Tag | Meaning |
| --- | --- |
| `latest` | most recent verified build |
| `YYYY-MM-DD` | date-stamped snapshot, useful as a citable reference |
| `sha-<short>` | git commit the image was built from |
| `hash-<12 hex>` | content hash of the build inputs (pins, notebooks, helpers, Dockerfile); used by CI to skip unchanged rebuilds |

## How Images Are Built and Verified

The `Build notebook images` workflow
(`.github/workflows/build-notebook-images.yml`) groups notebooks by directory
and pin set (`.github/scripts/build_notebook_image.py`), builds one image per
group from the parameterized `Dockerfile` in this directory, and then runs
every notebook in the group **inside the candidate image** using the same
harness the test workflows use (`.github/scripts/run_notebook.py`). An image
is pushed only if all of its notebooks execute successfully, so `latest` is
always a verified snapshot.

Inside the image the kernel environment is the system Python, with pins
installed via `uv pip install --system`, exactly matching the Colab bootstrap
cell and the CI harness. JupyterLab runs from an isolated `uv tool`
environment so its own dependencies cannot perturb the pinned kernel
environment. `ipykernel` and `nbformat` are the only additions to the pinned
set; they resolve jointly with the pins so a conflict fails the build rather
than silently changing a pinned version. The matplotlib font cache is built
at image-build time so the first import in a fresh container doesn't stall
on it.

Each architecture is built and verified on its own native runner
(`ubuntu-latest` for amd64, `ubuntu-24.04-arm` for arm64) — no emulation
anywhere in the pipeline — then the per-arch images are merged into one
multi-arch manifest carrying the user-facing tags.

## Maintainer Notes

- The workflow is currently `workflow_dispatch` only. The `filter` input is a
  regex on the notebook directory or path (default: the `001550/PaganLab`
  pilot); `push: false` gives a dry run (build + verify, no publish); `force`
  rebuilds even when the build-hash check says the published image is current.
- Rebuilds are skipped when a `hash-<...>` tag matching the current build
  inputs already exists on the registry. Changing a notebook, its pins, its
  helpers, or the Dockerfile changes the hash and triggers a rebuild. Pins are
  refreshed with `.github/scripts/lock_notebook.py` from the `requirements.in`
  committed next to the notebook (see `docs/adding-notebooks.md`).
- The base image is digest-pinned in the Dockerfile (`ARG BASE_IMAGE`). To
  bump it, update the digest, which changes every group's build hash, and
  dispatch a full rebuild. The `BASE_IMAGE` arg is also the knob for a future
  variant based on the official Colab runtime image.
- The server runs as the non-root user `jovyan` (uid 1000) with Jupyter's
  token auth enabled. CI's verification step runs the container with
  `--user root` so the harness's transient installs can write to the system
  Python; the published default stays non-root. The documented port mapping
  binds the host side to `127.0.0.1` explicitly; a bare `-p 8888:8888` would
  bind all interfaces, and on macOS it also loses silently to any local
  Jupyter server already listening on `127.0.0.1:8888`.
- The `hash-<12 hex>-amd64` / `-arm64` tags are the per-arch build artifacts
  the merge step assembles into the multi-arch `hash-<12 hex>` manifest; they
  also serve as the per-arch skip markers.
- Image eligibility follows `.github/notebook-test-exclusions.txt`, except
  that notebooks listed in `.github/notebook-image-inclusions.txt` are built
  anyway: the image ships system libraries (libgl1, libglib2.0-0, libxcb1)
  that the slim CI runner lacks, so some CI-excluded notebooks run fine in
  the image. They still must pass in-image verification to publish.
