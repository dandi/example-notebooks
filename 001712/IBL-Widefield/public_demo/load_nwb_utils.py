# Core data manipulation and analysis
from pathlib import Path

# NWB access
import h5py

# DANDI access
import remfile
from dandi.dandiapi import DandiAPIClient
from pynwb import NWBHDF5IO


def load_nwb_from_dandi(dandiset_id, subject_id, session_id, description):
    """
    Load NWB file from DANDI Archive via streaming.
    """
    pattern = f"sub-{subject_id}/sub-{subject_id}_ses-{session_id}_desc-{description}*.nwb"

    with DandiAPIClient() as client:
        assets = client.get_dandiset(dandiset_id, "draft").get_assets_by_glob(pattern=pattern, order="path")

        s3_urls = []
        for asset in assets:
            s3_url = asset.get_content_url(follow_redirects=1, strip_query=False)
            s3_urls.append(s3_url)

        if len(s3_urls) != 1:
            raise ValueError(f"Expected 1 file, found {len(s3_urls)} for pattern {pattern}")

        s3_url = s3_urls[0]

    file = remfile.File(s3_url)
    h5_file = h5py.File(file, "r")
    io = NWBHDF5IO(file=h5_file, load_namespaces=True)
    nwbfile = io.read()

    return nwbfile, io


def load_nwb_local(directory_path, subject_id, session_id, description):
    """
    Load NWB file from local directory.
    """
    directory_path = Path(directory_path)
    pattern = f"sub-{subject_id}/sub-{subject_id}_ses-{session_id}_desc-{description}*.nwb"
    matches = list(directory_path.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"Expected 1 file, found {len(matches)} for pattern {pattern}")
    nwbfile_path = matches[0]

    io = NWBHDF5IO(path=nwbfile_path, load_namespaces=True)
    nwbfile = io.read()

    return nwbfile, io
