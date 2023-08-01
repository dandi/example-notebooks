import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline import lab, experiment
from pipeline import dict_to_hash


# ==================== Brain Location =====================
brain_locations = [{'brain_location_name': 'left_m2',
                    'brain_area': 'M2',
                    'hemisphere': 'left',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'right_m2',
                    'brain_area': 'M2',
                    'hemisphere': 'right',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'both_m2',
                    'brain_area': 'M2',
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
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'left_pons',
                    'brain_area': 'PONS',
                    'hemisphere': 'left',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'right_pons',
                    'brain_area': 'PONS',
                    'hemisphere': 'right',
                    'skull_reference': 'Bregma'},
                   {'brain_location_name': 'both_pons',
                    'brain_area': 'PONS',
                    'hemisphere': 'both',
                    'skull_reference': 'Bregma'}]
experiment.BrainLocation.insert(brain_locations, skip_duplicates=True)
