import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline import lab, experiment
from pipeline import dict_to_hash


# ==================== Brain Location =====================
brain_locations = [{'brain_location_name': 'left_vm1',
                    'brain_area': 'vM1',
                    'hemisphere': 'left',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'right_vm1',
                    'brain_area': 'vM1',
                    'hemisphere': 'right',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'both_vm1',
                    'brain_area': 'vM1',
                    'hemisphere': 'both',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'left_alm',
                    'brain_area': 'ALM',
                    'hemisphere': 'left',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'right_alm',
                    'brain_area': 'ALM',
                    'hemisphere': 'right',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'both_alm',
                    'brain_area': 'ALM',
                    'hemisphere': 'both',
                    'skull_reference': 'Bregma'}]
experiment.BrainLocation.insert(brain_locations, skip_duplicates=True)
