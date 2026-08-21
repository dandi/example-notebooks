import datetime
import fnmatch
import json
import os
import shutil
import sys
from typing import List, Dict, Any, Optional

import requests
from jinja2 import Environment, FileSystemLoader
from dandi.dandiapi import DandiAPIClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_notebook_image import collect_groups  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COLAB_EXCLUSIONS = os.path.join(REPO_ROOT, ".github", "notebook-colab-exclusions.txt")
IMAGE_PREFIX = "ghcr.io/dandi/example-notebooks"


def image_is_public(group_name: str) -> bool:
    """True iff the group's image exists on GHCR and is anonymously pullable.

    Container packages start private and must be flipped public by hand, so
    the badge is derived from what an anonymous user can actually pull rather
    than from what CI has pushed.
    """
    repo = f"dandi/example-notebooks/{group_name}"
    try:
        token = requests.get(
            "https://ghcr.io/token", params={"scope": f"repository:{repo}:pull"},
            timeout=10,
        ).json().get("token")
        if not token:
            # No anonymous token grant: the package is private or does not exist.
            return False
        r = requests.get(
            f"https://ghcr.io/v2/{repo}/manifests/latest",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.oci.image.index.v1+json, "
                          "application/vnd.docker.distribution.manifest.list.v2+json",
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"GHCR check failed for {group_name}: {e}")
        return False


def docker_images_by_notebook() -> Dict[str, str]:
    """Map repo-relative notebook path -> public image ref (only public ones)."""
    mapping: Dict[str, str] = {}
    public: Dict[str, bool] = {}
    for group in collect_groups():
        if group.name not in public:
            public[group.name] = image_is_public(group.name)
        if not public[group.name]:
            continue
        for nb_name in group.notebooks:
            mapping[os.path.join(group.directory, nb_name)] = (
                f"{IMAGE_PREFIX}/{group.name}"
            )
    print(f"{sum(public.values())} of {len(public)} image groups are public")
    return mapping


def get_dandiset_metadata(dandiset_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata for a given dandiset ID.

    Parameters
    ----------
    dandiset_id : str
        The ID of the dandiset to fetch metadata for.

    Returns
    -------
    Optional[Dict[str, Any]]
        A dictionary containing the dandiset metadata if successful, None otherwise.
    """
    with DandiAPIClient() as client:
        try:
            dandiset = client.get_dandiset(dandiset_id)
            metadata = dandiset.get_raw_metadata()
            return metadata
        except Exception as e:
            print(f"Error fetching metadata for dandiset {dandiset_id}: {str(e)}")
            return None


def load_exclusion_patterns(path: str) -> List[str]:
    """Read gitignore-style glob patterns from an exclusion file."""
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


def is_excluded(rel_path: str, patterns: List[str]) -> bool:
    """Match a repo-relative path against gitignore-style patterns."""
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat):
            return True
        if pat.endswith("/**") and (
            rel_path == pat[:-3] or rel_path.startswith(pat[:-2])
        ):
            return True
    return False


def notebook_has_colab_bootstrap(abs_path: str) -> bool:
    """Return True iff the notebook starts with a Colab-bootstrap install cell."""
    try:
        with open(abs_path) as f:
            nb = json.load(f)
    except Exception:
        return False
    for cell in nb.get("cells", [])[:8]:
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        if "uv pip install --system" in source:
            return True
    return False


def find_notebooks(folder: str) -> List[str]:
    """
    Recursively find all Jupyter notebooks in a given folder.

    Parameters
    ----------
    folder : str
        The path to the folder to search in.

    Returns
    -------
    List[str]
        A list of relative paths to the found notebooks.
    """
    notebooks = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith('.ipynb'):
                rel_path = os.path.relpath(os.path.join(root, file), folder)
                notebooks.append(rel_path)
    return notebooks


def collect_metadata() -> List[Dict[str, Any]]:
    """
    Collect metadata and notebook information for all dandisets in the current directory.

    Each notebook is represented as a dict:
        {"path": "<relative-to-dandiset-folder>",
         "colab_eligible": bool,
         "colab_url": "<full https URL>" or ""}

    Notebooks are eligible for a Colab button iff (a) they begin with a
    Colab-bootstrap install cell and (b) their repo-relative path is not
    matched by any pattern in `.github/notebook-colab-exclusions.txt`.

    Note: the colab-exclusions list is intentionally independent of the
    CI test-exclusions list (`.github/notebook-test-exclusions.txt`). Some
    notebooks fail headless CI but work fine when a user opens them in
    Colab (eg notebooks that call `webbrowser.open()`, `input()`, or
    depend on libxcb — Colab handles all of those). Conversely, some
    notebooks pass headless CI but we still don't want to advertise them
    as one-click-runnable for other reasons.
    """
    colab_excl = load_exclusion_patterns(COLAB_EXCLUSIONS)
    docker_images = docker_images_by_notebook()

    dandisets = []
    for folder in os.listdir('.'):
        if os.path.isdir(folder) and folder.isdigit():
            metadata = get_dandiset_metadata(folder)
            if metadata:
                nb_paths = find_notebooks(folder)
                notebooks = []
                for rel in nb_paths:
                    repo_rel = os.path.join(folder, rel)
                    abs_path = os.path.join(REPO_ROOT, repo_rel)
                    excluded = is_excluded(repo_rel, colab_excl)
                    eligible = (not excluded) and notebook_has_colab_bootstrap(abs_path)
                    notebooks.append({
                        "path": rel,
                        "colab_eligible": eligible,
                        "colab_url": (
                            f"https://colab.research.google.com/github/"
                            f"dandi/example-notebooks/blob/master/{repo_rel}"
                            if eligible else ""
                        ),
                        "docker_image": docker_images.get(repo_rel, ""),
                    })
                dandisets.append({
                    'id': folder,
                    'metadata': metadata,
                    'notebooks': notebooks,
                })

    # newest dandisets first
    dandisets.sort(key=lambda x: x['id'], reverse=True)
    return dandisets


SITE_URL = "https://notebooks.dandiarchive.org"


def machine_readable_index(dandisets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A stable JSON view of the index for other sites (e.g. dandiset landing
    pages) to consume. Keys are additive; existing ones should not change."""
    out: Dict[str, Any] = {}
    for ds in dandisets:
        notebooks = []
        for nb in ds["notebooks"]:
            repo_rel = f"{ds['id']}/{nb['path']}"
            entry = {
                "path": repo_rel,
                "github_url": f"https://github.com/dandi/example-notebooks/blob/master/{repo_rel}",
                "colab_url": nb["colab_url"] or None,
                "docker_image": nb["docker_image"] or None,
                "docker_command": (
                    f"docker run --rm -p 127.0.0.1:8888:8888 {nb['docker_image']}:latest"
                    if nb["docker_image"] else None
                ),
            }
            notebooks.append(entry)
        out[ds["id"]] = {
            "index_url": f"{SITE_URL}/#dandiset-{ds['id']}",
            "notebooks": notebooks,
        }
    return {
        "schema_version": 1,
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": "https://github.com/dandi/example-notebooks",
        "index_url": f"{SITE_URL}/",
        "docker_help_url": f"{SITE_URL}/docker-help.html",
        "dandisets": out,
    }


def render_webpage(dandisets: List[Dict[str, Any]]) -> None:
    """
    Render the webpage using the collected dandiset information.

    Parameters
    ----------
    dandisets : List[Dict[str, Any]]
        A list of dictionaries containing information about each dandiset.

    Returns
    -------
    None
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(current_dir, '..', 'templates')

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('index.html')

    all_notebooks = [nb for ds in dandisets for nb in ds['notebooks']]
    stats = {
        'n_dandisets': len(dandisets),
        'n_notebooks': len(all_notebooks),
        'n_colab': sum(1 for nb in all_notebooks if nb['colab_eligible']),
        'n_docker': sum(1 for nb in all_notebooks if nb['docker_image']),
    }
    output = template.render(dandisets=dandisets, stats=stats)

    output_dir = os.path.join(current_dir, '..', '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'index.html'), 'w') as f:
        f.write(output)

    help_template = env.get_template('docker-help.html')
    with open(os.path.join(output_dir, 'docker-help.html'), 'w') as f:
        f.write(help_template.render(example_image="001550-paganlab"))

    with open(os.path.join(output_dir, 'notebooks.json'), 'w') as f:
        json.dump(machine_readable_index(dandisets), f, indent=2)

    assets_dir = os.path.join(template_dir, 'assets')
    if os.path.isdir(assets_dir):
        shutil.copytree(assets_dir, output_dir, dirs_exist_ok=True)

if __name__ == "__main__":
    dandisets = collect_metadata()
    render_webpage(dandisets)
