from datetime import datetime
import os
import re

import h5py as h5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from decimal import Decimal

import datajoint as dj
from pipeline import (reference, subject, utilities)

path = os.path.join('.', 'data', 'data', 'L4FS_loose_seal_ION_cut')
fname = 'JY1589AAAA.nwb'
nwb = h5.File(os.path.join(path, fname), 'r')

subject_info = {c: nwb['general']['subject'][c].value.decode('UTF-8')
                for c in ('subject_id', 'description', 'sex', 'species', 'weight', 'age', 'genotype')}
# force subject_id to be lower-case for consistency
subject_info['subject_id'] = subject_info['subject_id'].lower()

# dob and sex
subject_info['sex'] = subject_info['sex'][0].upper()
dob_str = re.search('(?<=Date of birth:\s)(.*)', subject_info['description'])
if utilities.parse_date(dob_str.group()) is not None:
    subject_info['date_of_birth'] = utilities.parse_date(dob_str.group())

# allele
allele_str = re.search('(?<=Animal Strain:\s)(.*)', subject_info['description']).group()  # extract the information related to animal allele
allele_dict = {alias.lower(): allele for alias, allele in subject.AlleleAlias.fetch()}
regex_str = '|'.join([re.escape(alias) for alias in allele_dict.keys()])
alleles = [allele_dict[s.lower()] for s in re.findall(regex_str, allele_str, re.I)]
# source
source_str = re.search('(?<=Animal source:\s)(.*)', subject_info['description']).group()  # extract the information related to animal allele
source_dict = {alias.lower(): source for alias, source in reference.AnimalSourceAlias.fetch()}
regex_str = '|'.join([re.escape(alias) for alias in source_dict.keys()])
subject_info['animal_source'] = source_dict[re.search(regex_str, source_str, re.I).group().lower()] if re.search(regex_str, source_str, re.I) else 'N/A'

session_time = utilities.parse_date(nwb['general']['session_id'].value.decode('UTF-8'))
session_info = dict(subject_info,
                    experiment_description = nwb['general']['experiment_description'].value.decode('UTF-8'),
                    institution = nwb['general']['institution'].value.decode('UTF-8'),
                    related_publications = nwb['general']['related_publications'].value.decode('UTF-8'),
                    session_id = nwb['general']['session_id'].value.decode('UTF-8'),
                    surgery = nwb['general']['surgery'].value.decode('UTF-8'),
                    identifier = nwb['identifier'].value.decode('UTF-8'),
                    nwb_version = nwb['nwb_version'].value.decode('UTF-8'),
                    session_note = nwb['session_description'].value.decode('UTF-8'),
                    session_time = session_time)

experimenters = nwb['general']['experimenter'].value.decode('UTF-8')
experiment_types = re.split('Experiment type: ', session_info['session_note'])[-1]
experiment_types = re.split(',\s?', experiment_types)

# experimenter and experiment type (possible multiple experimenters or types)
experimenters = [experimenters] if np.array(
    experimenters).size <= 1 else experimenters  # in case there's only 1 experimenter

# -------------- Intracellular --------
# -- read data - devices
devices = {d: nwb['general']['devices'][d].value.decode('UTF-8') for d in nwb['general']['devices']}

# -- read data - intracellular_ephys
ie_info = {c: nwb['general']['intracellular_ephys']['loose_seal_1'][c].value.decode('UTF-8') for c in nwb['general']['intracellular_ephys']['loose_seal_1']}

brain_region = re.split(',\s?', ie_location)[-1]
coord_ap_ml_dv = re.findall('\d+.\d+', ie_info['location'])

# hemisphere: left-hemisphere is ipsi, so anything contra is right
brain_region, hemisphere = utilities.get_brain_hemisphere(brain_region)
brain_location = {'brain_region': 'barrel',
                  'brain_subregion': 'N/A',
                  'cortical_layer': '4',
                  'hemisphere': hemisphere}
# -- ActionLocation
action_location = dict(brain_location,
                       coordinate_ref = 'bregma',
                       coordinate_ap = round(Decimal(coord_ap_ml_dv[0]), 2),
                       coordinate_ml = round(Decimal(coord_ap_ml_dv[1]), 2),
                       coordinate_dv = round(Decimal(coord_ap_ml_dv[2])* Decimal('1e-3'), 2))  # convert um -> mm
# -- Whole Cell Device
ie_device = nwb['general']['intracellular_ephys']['whole_cell']['device'].value

# -- Cell
cell_id = re.split('.nwb', session_info['session_id'])[0]
cell_key = dict({**subject_info, **session_info, **action_location},
                cell_id = cell_id,
                cell_type = 'N/A',
                device_name = ie_device)


for idx, fname in enumerate(fnames):
    print(idx)
    nwb = h5.File(fname, 'r')
    # trial_type=[v['description'].value.decode('UTF-8') for v in nwb['epochs'].values()]
    # print(set(trial_type))
    whisker_configs = ([wk.decode('UTF-8') for wk in nwb["general"]["whisker_configuration"].value]
                       if nwb["general"]["whisker_configuration"].value.shape
                       else [wk for wk in nwb["general"]["whisker_configuration"].value.decode('UTF-8').split(',')])
    print(whisker_configs)

fname = fnames[53]
nwb = h5.File(fname, 'r')
trial_type = [v['description'].value.decode('UTF-8') for v in nwb['epochs'].values()]
print(set(trial_type))
photostim_data1 = nwb['stimulus']['presentation']['photostimulus_1']['data'].value
plt.plot(photostim_data1)
photostim_data2 = nwb['stimulus']['presentation']['photostimulus_2']['data'].value
plt.plot(photostim_data2)

whisker_timeseries = nwb['processing']['whisker']['BehavioralTimeSeries']
whisker_num = '1'
distance_to_pole = whisker_timeseries['distance_to_pole_' + whisker_num]['data'].value.flatten()
touch_offset = whisker_timeseries['touch_offset_' + whisker_num]['data'].value.flatten()
touch_onset = whisker_timeseries['touch_onset_' + whisker_num]['data'].value.flatten()
whisker_angle = whisker_timeseries['whisker_angle_' + whisker_num]['data'].value.flatten()
whisker_curvature = whisker_timeseries['whisker_curvature_' + whisker_num]['data'].value.flatten()
behavior_timestamps = whisker_timeseries['distance_to_pole_' + whisker_num]['timestamps'].value * 1e-3  # convert msec->second

plt.plot(whisk_pos, 'g')
plt.plot(whisk_pos*touch_on, '.', c='deepskyblue')

plt.plot(behavior_timestamps*1e-3, whisker_angle)
plt.plot(behavior_timestamps*1e-3, whisker_curvature)

b_fs = 1 / np.median(np.diff(behavior_timestamps))

# recreate matlab script
twhisker = whisker_timeseries['distance_to_pole_' + whisker_num]['timestamps'].value
diffwhiskertime = np.diff(twhisker)

np.where(diffwhiskertime>1)

index_whiskertrial_starts=np.hstack([0 , 1+np.where(diffwhiskertime>1)[0]]);
index_whiskertrial_ends=np.hstack([1+np.where(diffwhiskertime>1)[0], len(twhisker)-1]);

trial_whiskerstarts_1= twhisker[index_whiskertrial_starts];
trial_whiskerends_1= twhisker[index_whiskertrial_ends];

start_times = [v['start_time'].value for v in nwb['epochs'].values()]
stop_times = [v['stop_time'].value for v in nwb['epochs'].values()]

tr = 0
print(f'{start_times[tr]} ; {stop_times[tr]}')
print(f'{trial_whiskerstarts_1[tr]*1e-3} ; {trial_whiskerends_1[tr]*1e-3}')

timeall = nwb['acquisition']['timeseries']['membrane_potential']['timestamps'].value

fig1, ax1 = plt.subplots(1,1)
ax1.plot(twhisker, '.')

fig2, ax2 = plt.subplots(1,1)
ax2.plot(timeall, '.')

# =======================
import pickle
import hashlib

d = intracellular.UnitSpikeTimes.fetch(as_dict=True, limit=1)[0]

d_pkl = pickle.dumps(d)

d_hash = hashlib.md5(d_pkl).hexdigest()

schema = dj.schema(dj.config['custom']['database.prefix'] + 'analysis')

@schema
class Timer(dj.Manual):
    definition = """
    id: smallint
    entry_time = CURRENT_TIMESTAMP: timestamp
    """
# -------------------------------------
import re

fake_match = 'Houston  Chronicle; Business & Finance'
begin_strings = ['The', 'A', 'And', '0']
end_strings = ['Co', 'Comp', 'LLC']
connecting_words = ['and', 'or', 'for', 'of']

def match_and_check_results(orig_s, option_list):
    if orig_s in option_list:
        return orig_s
    return None


def get_option_list(search_string):
    return []


orig_s = 'Houston Chronicle Business And Finance'
search_string = orig_s
found = None

and_swap = False  # and <-> &
while not found:
    print(search_string)
    # get the option list
    options = get_option_list(search_string)

    # try to match the returned list of results
    matched_s = match_and_check_results(orig_s, options)
    if matched_s:
        found = matched_s
        break

    if len(search_string.split()) == 1:
        break

    # Remove begin-filter and end-filter words
    # Remove special characters

    # Swap & <-> And
    if not and_swap:
        if re.search('and', search_string, flags=re.I):
            search_string = re.sub('and', '&', search_string, flags=re.I)
            and_swap = True
        elif re.search('&', search_string):
            search_string = re.sub('&', 'And', search_string)
            and_swap = True
        else:
            and_swap = True
    else:
        # remove trailing connecting words
        re_s = '|'.join([r'\s' + w + r'$' for w in connecting_words])
        search_string = re.sub(re_s, '', search_string)
        # remove the last word
        search_string = ''.join(search_string.split()[:-1])

# Go the reverse direction
search_string = orig_s
and_swap = False  # and <-> &
while not found:
    print(search_string)
    # get the option list
    options = get_option_list(search_string)

    # try to match the returned list of results
    matched_s = match_and_check_results(orig_s, options)
    if matched_s:
        found = matched_s
        break

    if len(search_string.split()) == 1:
        break

    # Remove begin-filter and end-filter words
    # Remove special characters

    # Swap & <-> And
    if not and_swap:
        if re.search('and', search_string, flags=re.I):
            search_string = re.sub('and', '&', search_string, flags=re.I)
            and_swap = True
        elif re.search('&', search_string):
            search_string = re.sub('&', 'And', search_string)
            and_swap = True
        else:
            and_swap = True
    else:
        # remove trailing connecting words
        re_s = '|'.join([r'\s' + w + r'$' for w in connecting_words])
        search_string = re.sub(re_s, '', search_string)
        # remove the first word
        search_string = ''.join(search_string.split()[1:])


















