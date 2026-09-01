from pynwb import NWBHDF5IO
import remfile
import h5py
from dandi.dandiapi import DandiAPIClient

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
        client.dandi_authenticate()
        asset = client.get_dandiset(DANDISET_ID, 'draft').get_asset_by_path(file_path)
        s3_url = asset.get_content_url(follow_redirects=1, strip_query=False)
    file_system = remfile.File(s3_url)
    file = h5py.File(file_system, mode="r")
    io = NWBHDF5IO(file=file, load_namespaces=True)
    nwbfile = io.read()
    return nwbfile, io