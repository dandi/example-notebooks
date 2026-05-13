import fnmatch
import json
import os
from typing import List, Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader
from dandi.dandiapi import DandiAPIClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_EXCLUSIONS = os.path.join(REPO_ROOT, ".github", "notebook-test-exclusions.txt")
COLAB_EXCLUSIONS = os.path.join(REPO_ROOT, ".github", "notebook-colab-exclusions.txt")


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
    matched by any pattern in `.github/notebook-test-exclusions.txt` or
    `.github/notebook-colab-exclusions.txt`.
    """
    test_excl = load_exclusion_patterns(TEST_EXCLUSIONS)
    colab_excl = load_exclusion_patterns(COLAB_EXCLUSIONS)
    all_excl = test_excl + colab_excl

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
                    excluded = is_excluded(repo_rel, all_excl)
                    eligible = (not excluded) and notebook_has_colab_bootstrap(abs_path)
                    notebooks.append({
                        "path": rel,
                        "colab_eligible": eligible,
                        "colab_url": (
                            f"https://colab.research.google.com/github/"
                            f"dandi/example-notebooks/blob/master/{repo_rel}"
                            if eligible else ""
                        ),
                    })
                dandisets.append({
                    'id': folder,
                    'metadata': metadata,
                    'notebooks': notebooks,
                })

    dandisets.sort(key=lambda x: x['id'])
    return dandisets


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

    output = template.render(dandisets=dandisets)

    output_dir = os.path.join(current_dir, '..', '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'index.html'), 'w') as f:
        f.write(output)

if __name__ == "__main__":
    dandisets = collect_metadata()
    render_webpage(dandisets)
