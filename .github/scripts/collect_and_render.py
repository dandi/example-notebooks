import os
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
from dandi.dandiapi import DandiAPIClient


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

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, each containing information about a dandiset,
        sorted by dandiset ID.
    """
    dandisets = []
    for folder in os.listdir('.'):
        if os.path.isdir(folder) and folder.isdigit():
            metadata = get_dandiset_metadata(folder)
            if metadata:
                notebooks = find_notebooks(folder)
                dandisets.append({
                    'id': folder,
                    'metadata': metadata,
                    'notebooks': notebooks
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
