from caveclient import CAVEclient
from datetime import datetime
import numpy as np
import json

"""
Table Queries
"""
client = CAVEclient("minnie65_phase3_v1")
apl_functional_coreg_forward_v5 = client.materialize.live_query('apl_functional_coreg_forward_v5', timestamp=datetime.utcnow())
nucleus_neuron_svm = client.materialize.live_query('nucleus_neuron_svm', timestamp=datetime.utcnow())

MINNIE_RESOLUTION = np.array([4,4,40])

def generate_functional_ng_state(unit_info, table = apl_functional_coreg_forward_v5):
    unit_info = [int(x) for x in unit_info]
    ref_ng_state = json.load(open('ng_visualization/functional_base_state.json','r'))
    fields = ref_ng_state['layers'][1]['source']
    base_url = 'precomputed://s3://bossdb-open-data/iarpa_microns/minnie/functional_data/field_seg_masks/'

    def gen_compact_roi_layer(field_list):
        source_list = []
        for field in field_list:
            field = field.copy()
            field_name = field['url'].split('/')[-1]
            field['url'] = base_url+field_name
            source_list.extend([field])

        return {'type':"segmentation",
                "source":source_list,
                "tab":"source",
                "segments": [],
                "segmentQuery":[],
                "name":"all_annotations",
                "visible": False}

    def get_roi_layer(field, unit_field_id):
        field_name = field['url'].split('/')[-1]
        field['url'] = base_url+field_name
        return {'type':"segmentation",
                "source":field,
                "tab":"source",
                "segments": [unit_field_id],
                "segmentQuery":[],
                "name":field_name + '_anno'}

    ref_ng_state['layers'].extend([gen_compact_roi_layer(fields)])
    session_id, scan_id, field_id, unit_field_id = unit_info
    unit_id_row = table[(table['session']==session_id)&(table['field'] == field_id)&(table['scan_idx']==scan_id)&(table['unit_id'] == unit_field_id)].iloc[0]
    field_obj = fields[unit_id_row['field']-1].copy()
    ref_ng_state['position'] = list(np.array(field_obj['transform']['matrix'])[:,-1])
    ref_ng_state['layers'].extend([get_roi_layer(field_obj, unit_field_id=unit_field_id)])

    target_id = unit_id_row.target_id

    return ref_ng_state, target_id


def generate_structural_ng_state(target_id, table = nucleus_neuron_svm):
    """
    update structural ng state with associate seg_id and center at position
    """
    target_id_row = table[table['id'] == target_id]
    pt_root_id = target_id_row.pt_root_id.values[0]
    pt_position = [int(x) for x in target_id_row.pt_position.values[0]]
    base_structural_state =  json.load(open('ng_visualization/structural_base_state.json','r'))
    base_structural_state['layers'][1]['segments'].extend([str(pt_root_id)])
    base_structural_state['navigation']['pose']['position']['voxelCoordinates'].extend(pt_position)

    return base_structural_state

def save_json(filename, json_data):
    """
    utility function to generate jsons with states
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    
