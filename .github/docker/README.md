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

Images are built for `linux/amd64`, the platform the dependency pins were
resolved for. On Apple Silicon, Docker Desktop runs them under emulation;
pass `--platform linux/amd64` to silence the platform warning.

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
than silently changing a pinned version.

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
- Images run as root (`python:3.12-slim` has no unprivileged user) and keep
  Jupyter's token auth enabled. The documented port mapping binds the host
  side to `127.0.0.1` explicitly; a bare `-p 8888:8888` would bind all
  interfaces, and on macOS it also loses silently to any local Jupyter server
  already listening on `127.0.0.1:8888`.
