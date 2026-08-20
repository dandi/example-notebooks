# syntax=docker/dockerfile:1
# Environment image for DANDI example notebooks. Built by
# .github/workflows/build-notebook-images.yml from a context prepared by
# .github/scripts/build_notebook_image.py (requirements.txt + work/).
#
# Two separate Python environments by design:
#   - the kernel env is the system Python (/usr/local): pins go in with
#     `uv pip install --system`, matching both the Colab bootstrap cell and
#     run_notebook.py, so the CI harness runs unmodified inside the image
#     (CI runs it with --user root so its transient installs can write there);
#   - JupyterLab lives in an isolated `uv tool` env so its own dependency
#     tree can never upgrade or downgrade anything in the pinned kernel env.
#
# The server runs as the non-root user jovyan (uid 1000).

ARG BASE_IMAGE=python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a
FROM ${BASE_IMAGE}

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /bin/bash jovyan

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/

# The tool env lives under /opt (not /root) so it is readable by jovyan.
ARG JUPYTERLAB_VERSION=4.6.3
ENV UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/opt/uv-bin
RUN uv tool install "jupyterlab==${JUPYTERLAB_VERSION}"
# JUPYTER_PATH makes the pinned kernelspec under /usr/local win over the
# kernelspec that ships inside the JupyterLab tool env.
ENV PATH="/opt/uv-bin:${PATH}" \
    JUPYTER_PATH=/usr/local/share/jupyter

# ipykernel and nbformat resolve jointly with the pins in one invocation so
# any conflict fails the build instead of silently changing a pinned version.
# gcc/libc6-dev cover pins with no wheel for the target arch (e.g. old psutil
# on arm64) and are purged in the same layer to keep the image slim.
COPY requirements.txt /tmp/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && uv pip install --system --no-cache -r /tmp/requirements.txt ipykernel nbformat \
    && python -m ipykernel install --name python3 --display-name "Python 3 (pinned)" \
    && apt-get purge -y gcc libc6-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY --chown=jovyan:jovyan work/ /work/

USER jovyan
ENV HOME=/home/jovyan

# Matplotlib builds its font cache on first import; do it at build time (as
# jovyan, so the cache lands in the home directory the server runs from) so
# the first cell a user runs doesn't stall on it. Under Rosetta emulation the
# subprocess spawn involved can even deadlock, so it must not happen at runtime.
RUN python - <<'PYEOF'
try:
    import matplotlib.pyplot  # noqa: F401
except ImportError:
    pass
PYEOF

ARG DEFAULT_NOTEBOOK
ARG BUILD_HASH
ARG GIT_SHA=unknown
ARG NOTEBOOKS=""
ENV DEFAULT_NOTEBOOK=${DEFAULT_NOTEBOOK}
LABEL org.opencontainers.image.source="https://github.com/dandi/example-notebooks" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.dandiarchive.notebooks="${NOTEBOOKS}" \
      org.dandiarchive.build-hash="${BUILD_HASH}"

EXPOSE 8888
CMD jupyter-lab --ip=0.0.0.0 --port=8888 --no-browser \
    --ServerApp.default_url="/lab/tree/${DEFAULT_NOTEBOOK}"
