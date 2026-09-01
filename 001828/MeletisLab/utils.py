import os

import h5py
import remfile
from dandi.dandiapi import DandiAPIClient
from pynwb import NWBHDF5IO

DANDISET_ID = "001828"


def _client():
    return DandiAPIClient(token=os.environ.get("DANDI_API_KEY"))


def get_asset(session_id: str):
    """Return the DANDI asset matching session_id (needed for video widgets)."""
    with _client() as client:
        dandiset = client.get_dandiset(DANDISET_ID, "draft")
        return next(
            a for a in dandiset.get_assets()
            if session_id in a.path and a.path.endswith(".nwb")
        )


def stream_nwb(session_id: str):
    """Stream an NWB file from DANDI by matching session_id against asset paths."""
    asset = get_asset(session_id)
    s3_url = asset.get_content_url(follow_redirects=4, strip_query=False)
    rf = remfile.File(s3_url)
    f = h5py.File(rf, mode="r")
    io = NWBHDF5IO(file=f)
    return io.read()
