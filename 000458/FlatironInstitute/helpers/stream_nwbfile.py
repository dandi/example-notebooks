# See 000_lindi_vs_fsspec_streaming.py for why lindi is used rather than fsspec.

from pynwb import NWBHDF5IO
from dandi.dandiapi import DandiAPIClient
import lindi


def stream_nwbfile(DANDISET_ID, file_path):
    '''Stream NWB file from DANDI archive.

    Parameters
    ----------
    DANDISET_ID : str
        Dandiset ID
    file_path : str
        Path to NWB file in DANDI archive

    Returns
    -------
    nwbfile : NWBFile
        NWB file
    io : NWBHDF5IO
        NWB IO object (for closing)

    Notes
    -----
    The io object must be closed after use.
    '''
    with DandiAPIClient() as client:
        asset = client.get_dandiset(DANDISET_ID, 'draft').get_asset_by_path(file_path)
        asset_url = asset.get_content_url(follow_redirects=0, strip_query=True)
    file = lindi.LindiH5pyFile.from_hdf5_file(asset_url)
    io = NWBHDF5IO(file=file, load_namespaces=True)
    nwbfile = io.read()
    return nwbfile, io
