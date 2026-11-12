from typing import Literal

import dandi.dandiapi
import h5py
import pynwb
import remfile

def stream_nwbfile(subject_id: str, session_id: str, session_type: Literal["imaging", "segmentation"]) -> pynwb.NWBFile:
    dandiset_id = "001075"
    dandiset_version = "0.240930.1859"
    dandifile_path = f"sub-{subject_id}/sub-{subject_id}_ses-{session_id}_desc-{session_type}_ophys+ogen.nwb"

    dandi_client = dandi.dandiapi.DandiAPIClient()
    dandiset = dandi_client.get_dandiset(dandiset_id=dandiset_id, version_id=dandiset_version)
    dandifile = dandiset.get_asset_by_path(path=dandifile_path)
    s3_url = dandifile.get_content_url()
    byte_stream = remfile.File(url=s3_url)
    file = h5py.File(name=byte_stream)
    io = pynwb.NWBHDF5IO(file=file)
    nwbfile = io.read()

    return nwbfile