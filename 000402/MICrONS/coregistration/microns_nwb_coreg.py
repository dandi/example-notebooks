##############################################################################################
# Copyright 2023 The Johns Hopkins University Applied Physics Laboratory LLC
# All rights reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this 
# software and associated documentation files (the "Software"), to deal in the Software 
# without restriction, including without limitation the rights to use, copy, modify, 
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE 
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE 
# OR OTHER DEALINGS IN THE SOFTWARE.
##############################################################################################

"""
This script contains all functions necessary to update a MICrONS NWB file with the latest automated coregistration from CAVE. 

Check the DANDISET and CAVE_COREG_TABLE variables before running to make sure they are the correct dataset and tables
you want to pull.

DEV NOTE: Unable to update NWB file for session 5 scan 7. 

Example Usage:
```
from microns_nwb_coreg import get_microns_nwb_file, update_microns_nwb_file

microns_nwb = get_microns_nwb_file(session_no=4, scan_no=4)
microns_nwb = update_microns_nwb_file(microns_nwb)
"""

from dandi.dandiapi import DandiAPIClient
from caveclient import CAVEclient

from fsspec.implementations.cached import CachingFileSystem
from fsspec import filesystem
from h5py import File
from pynwb import NWBHDF5IO
from pynwb.file import NWBFile

from tqdm import tqdm
import pandas as pd

from pynwb.ophys import PlaneSegmentation


DANDISET_ID = "000402"
CAVE_COREG_TABLE = "apl_functional_coreg_forward_v5"


def get_microns_nwb_file(session_no:int, scan_no:int):
    file_path = f"sub-17797/sub-17797_ses-{session_no}-scan-{scan_no}_behavior+image+ophys.nwb"
    with DandiAPIClient() as client:
        asset = client.get_dandiset(DANDISET_ID, 'draft').get_asset_by_path(file_path)
        s3_url = asset.get_content_url(follow_redirects=1, strip_query=True)

    # First, create a virtual filesystem based on the http protocol
    fs = filesystem("http")

    # Create a cache to save downloaded data to disk (optional)
    fs = CachingFileSystem(
        fs=fs,
        cache_storage="nwb-cache",  # Local folder for the cache
    )

    # Next, open the file with NWBHDF5IO
    file_system = fs.open(s3_url, "rb")
    file = File(file_system, mode="r")
    io = NWBHDF5IO(file=file, load_namespaces=True)

    microns_data = io.read()
    return microns_data

def create_new_plane_segmentation(old, df, descriptions):
    ps = PlaneSegmentation(
        name=old.name, 
        description=old.description, 
        imaging_plane=old.imaging_plane,
        id=df.index.tolist()
    )
    
    for col in df.columns:
        if col in old.colnames:
            old_col = find_column_by_name(old, col)
            ps.add_column(name=old_col.name, description=old_col.description, data=df[col].tolist())
        else:
            ps.add_column(name=col, description=descriptions[col], data=df[col].tolist())
    return ps
        

def find_column_by_name(table,col_name):
    for c in table.columns:
        if c.name == col_name:
            return c
        
def update_microns_nwb_file(
    nwb: NWBFile
):

    # Pre-requisite data loading
    cave = CAVEclient("minnie65_phase3_v1")
    coreg = cave.materialize.query_table(CAVE_COREG_TABLE)
    scan_units = pd.read_pickle("./ScanUnit.pkl")

    session, scan_idx = int(nwb.session_id.split('-')[0]), int(nwb.session_id.split('-')[2])
    if session == 5 and scan_idx == 7:
        print("Error: This file does not contain a unit_id column")
        return 
    scan_units_modified = scan_units[(scan_units['session']==session) & (scan_units['scan_idx']==scan_idx)]
    
    image_segmentation = nwb.processing["ophys"].data_interfaces["ImageSegmentation"]
    
    all_ps = list(image_segmentation.plane_segmentations)
    for ps_name in tqdm(all_ps):
        
        ps = image_segmentation.plane_segmentations.pop(ps_name)
        field = int(ps_name[-1])
        field_scan_units = scan_units_modified[scan_units_modified['field'] == field]
        ps_df = ps[:]
        ps_df['mask_id'] = ps_df.index
        ps_df_with_units = ps_df.merge(field_scan_units, on='mask_id', how='left').drop(columns=[
            'mask_id', 'session', 'scan_idx', 'field'
        ])
        
        coreg_units = coreg[
            (coreg['session']==session) & 
            (coreg['scan_idx']==scan_idx) & 
            (coreg['field'] == field)
        ][['target_id', 'unit_id']]
        
        if len(coreg_units):
            ps_df_with_units = ps_df_with_units.merge(coreg_units, on='unit_id').rename(
                columns={
                    'target_id': 'auto_match_cave_nuclei_id', 
                    'cave_ids': 'manual_match_cave_nuclei_id'
                }
            )
        
        description = {x: "Placeholder" for x in ps_df_with_units.columns}
        new_ps = create_new_plane_segmentation(ps, ps_df_with_units, description)
        image_segmentation.plane_segmentations.add(new_ps)
        
    return nwb