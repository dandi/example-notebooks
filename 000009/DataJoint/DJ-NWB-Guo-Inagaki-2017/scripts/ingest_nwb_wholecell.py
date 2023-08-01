# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 16:22:42 2018

@author: thinh
"""
import os
import re
import pathlib
import h5py as h5
import numpy as np
from decimal import Decimal
import datajoint as dj

from pipeline import (reference, subject, acquisition, stimulation, analysis,
                      intracellular, extracellular, behavior, utilities)


# ================== Dataset ==================
path = pathlib.Path(dj.config['custom'].get('intracellular_directory')).as_posix()
fnames = os.listdir(path)

for fname in fnames:
    try:
        nwb = h5.File(os.path.join(path, fname), 'r')
        print(f'File loaded: {fname}')
    except:
        print('=================================')
        print(f'!!! ERROR LOADING FILE: {fname}')   
        print('=================================')
        continue
    
    # ========================== METADATA ==========================
    # ==================== subject ====================
    subject_info = {c: nwb['general']['subject'][c].value.decode('UTF-8')
                    for c in ('subject_id', 'description', 'sex', 'species', 'weight', 'age', 'genotype')}
    # force subject_id to be lower-case for consistency
    subject_info['subject_id'] = subject_info['subject_id'].lower()

    # dob and sex
    subject_info['sex'] = subject_info['sex'][0].upper()
    dob_str = re.search('(?<=Date of birth:\s)(.*)', subject_info['description'])
    if utilities.parse_prefix(dob_str.group()) is not None:
        subject_info['date_of_birth'] = utilities.parse_prefix(dob_str.group())
        
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

    with subject.Subject.connection.transaction:
        if subject_info not in subject.Subject.proj():
            subject.Subject.insert1(subject_info, ignore_extra_fields=True)
            subject.Subject.Allele.insert((dict(subject_info, allele = k)
                                           for k in alleles), ignore_extra_fields = True)

    # ==================== session ====================
    # -- session_time
    session_time = utilities.parse_prefix(nwb['session_start_time'].value)
    if session_time is not None:
        session_info = dict(
            experiment_description=nwb['general']['experiment_description'].value,
            institution=nwb['general']['institution'].value,
            related_publications=nwb['general']['related_publications'].value.decode('UTF-8'),
            session_id=nwb['general']['session_id'].value,
            surgery=nwb['general']['surgery'].value.decode('UTF-8'),
            identifier=nwb['identifier'].value,
            nwb_version=nwb['nwb_version'].value,
            session_note=nwb['session_description'].value,
            session_time=session_time)

        experimenters = nwb['general']['experimenter'].value
        experiment_types = re.split('Experiment type: ', session_info['session_note'])[-1]
        experiment_types = re.split(',\s?', experiment_types)

        # experimenter and experiment type (possible multiple experimenters or types)
        experimenters = [experimenters] if np.array(experimenters).size <= 1 else experimenters  # in case there's only 1 experimenter

        reference.Experimenter.insert(zip(experimenters), skip_duplicates = True)
        acquisition.ExperimentType.insert(zip(experiment_types), skip_duplicates = True)

        with acquisition.Session.connection.transaction:
            if dict(subject_info, session_time = session_time) not in acquisition.Session.proj():
                acquisition.Session.insert1({**subject_info, **session_info}, ignore_extra_fields=True)
                acquisition.Session.Experimenter.insert((dict({**subject_info, **session_info}, experimenter=k) for k in experimenters), ignore_extra_fields=True)
                acquisition.Session.ExperimentType.insert((dict({**subject_info, **session_info}, experiment_type=k) for k in experiment_types), ignore_extra_fields=True)
            print(f'Creating Session - Subject: {subject_info["subject_id"]} - Date: {session_info["session_time"]}')

    # ==================== Trials ====================
    trial_key = {'subject_id': subject_info["subject_id"], 'session_time': session_info["session_time"]}
    # -- read trial-related info -- nwb['epochs'], nwb['analysis'], nwb['stimulus']['presentation'])
    trial_details = dict(trial_names=[tr for tr in nwb['epochs']],
                         trial_descs=[v['description'].value for v in nwb['epochs'].values()],
                         start_times=[v['start_time'].value for v in nwb['epochs'].values()],
                         stop_times=[v['stop_time'].value for v in nwb['epochs'].values()],
                         good_trials=nwb['analysis']['good_trials'].value,
                         trial_type_string=nwb['analysis']['trial_type_string'].value,
                         trial_type_mat=nwb['analysis']['trial_type_mat'].value,
                         cue_start_times=nwb['stimulus']['presentation']['cue_start']['timestamps'].value,
                         cue_end_times=nwb['stimulus']['presentation']['cue_end']['timestamps'].value,
                         pole_in_times=nwb['stimulus']['presentation']['pole_in']['timestamps'].value,
                         pole_out_times=nwb['stimulus']['presentation']['pole_out']['timestamps'].value)

    # form new key-values pair and insert key
    trial_key['trial_counts'] = len(trial_details['trial_names'])

    if trial_key not in acquisition.TrialSet.proj():
        acquisition.TrialSet.insert1(trial_key, allow_direct_insert=True)
        print(f'Inserted trial set for: Subject: {subject_info["subject_id"]} - Date: {session_info["session_time"]}')
        print('Inserting trial ID: ', end="")
        # loop through each trial and insert
        for idx, trial_id in enumerate(trial_details['trial_names']):
            trial_id = int(re.search('\d+', trial_id).group())
            trial_key['trial_id'] = trial_id
            # -- start/stop time
            trial_key['start_time'] = trial_details['start_times'][idx]
            trial_key['stop_time'] = trial_details['stop_times'][idx]
            # ======== Now add trial descriptors ====
            # -- good/bad trial_status (nwb['analysis']['good_trials'])
            trial_key['trial_is_good'] = True if trial_details['good_trials'].flatten()[idx] == 1 else False
            trial_code = trial_details['trial_type_mat'][idx]

            # -- trial type --
            if trial_code[1] or trial_code[3]:
                trial_key['trial_type'] = 'lick left'
            elif trial_code[0] or trial_code[2]:
                trial_key['trial_type'] = 'lick right'
            else:
                trial_key['trial_type'] = 'non-performing'
            # -- trial response --
            if trial_code[4]:
                trial_key['trial_response'] = 'early lick'
            elif trial_code[0] or trial_code[1]:
                trial_key['trial_response'] = 'correct'
            elif trial_code[2] or trial_code[3]:
                trial_key['trial_response'] = 'incorrect'
            elif trial_code[5]:
                trial_key['trial_response'] = 'no response'
            # -- trial stim --
            trial_key['trial_stim_present'] = bool(trial_code[-1])
            # insert
            acquisition.TrialSet.Trial.insert1(trial_key, ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
            # ======== Now add trial event timing to the EventTime part table ====
            # -- events timing
            acquisition.TrialSet.EventTime.insert((dict(trial_key, trial_event=k, event_time = trial_details[e][idx])
                                                    for k, e in zip(('trial_start', 'trial_stop', 'cue_start',
                                                                     'cue_end', 'pole_in', 'pole_out'),
                                                                    ('start_times', 'stop_times', 'cue_start_times',
                                                                     'cue_end_times', 'pole_in_times', 'pole_out_times'))),
                                                   ignore_extra_fields=True, allow_direct_insert=True)
            print(f'{trial_id} ', end="")
        print('')

    # ==================== Intracellular ====================
    # -- read data - devices
    devices = {d: nwb['general']['devices'][d].value.decode('UTF-8') for d in nwb['general']['devices']}
        
    # -- read data - intracellular_ephys
    ie_filtering = nwb['general']['intracellular_ephys']['whole_cell']['filtering'].value

    ie_location = nwb['general']['intracellular_ephys']['whole_cell']['location'].value
    brain_region = re.split(',\s?', ie_location)[-1]
    coord_ap_ml_dv = re.findall('\d+.\d+', ie_location)
    
    # hemisphere: left-hemisphere is ipsi, so anything contra is right
    brain_region, hemisphere = utilities.get_brain_hemisphere(brain_region)
    brain_location = {'brain_region': brain_region,
                      'brain_subregion': 'N/A',
                      'cortical_layer': 'N/A',
                      'hemisphere': hemisphere}
    # -- BrainLocation
    if brain_location not in reference.BrainLocation.proj():
        reference.BrainLocation.insert1(brain_location)
    # -- ActionLocation
    action_location = dict(brain_location,
                           coordinate_ref='bregma',
                           coordinate_ap=round(Decimal(coord_ap_ml_dv[0]), 2),
                           coordinate_ml=round(Decimal(coord_ap_ml_dv[1]), 2),
                           coordinate_dv=round(Decimal(coord_ap_ml_dv[2]), 2))
    if action_location not in reference.ActionLocation.proj():
        reference.ActionLocation.insert1(action_location)
    
    # -- Whole Cell Device
    ie_device = nwb['general']['intracellular_ephys']['whole_cell']['device'].value
    if {'device_name': ie_device} not in reference.WholeCellDevice.proj():
        reference.WholeCellDevice.insert1({'device_name': ie_device, 'device_desc': devices[ie_device]})
    
    # -- Cell
    cell_id = re.split('.nwb', session_info['session_id'])[0]
    cell_key = dict({**subject_info, **session_info, **action_location},
                                  cell_id=cell_id,
                                  cell_type='N/A',
                                  device_name=ie_device)
    if cell_key not in intracellular.Cell.proj():
        intracellular.Cell.insert1(cell_key, ignore_extra_fields=True)

    # ==================== Photo stimulation ====================    
    # -- read data - optogenetics
    opto_site_name = list(nwb['general']['optogenetics'].keys())[0]
    opto_descs = nwb['general']['optogenetics'][opto_site_name]['description'].value.decode('UTF-8')
    opto_excitation_lambda = (re.search("\d+",
                                        nwb['general']['optogenetics'][opto_site_name]['excitation_lambda']
                                        .value.decode('UTF-8')).group())
    splittedstr = re.split(',\s?coordinates:\s?', nwb['general']['optogenetics'][opto_site_name]['location'].value.decode('UTF-8'))
    brain_region = splittedstr[0]
    coord_ap_ml_dv = re.findall('\d+\.\d+', splittedstr[-1])
    
    # hemisphere: left-hemisphere is ipsi, so anything contra is right-hemisphere
    brain_region, hemisphere = utilities.get_brain_hemisphere(brain_region)
    brain_location = {'brain_region': brain_region,
                      'brain_subregion': 'N/A',
                      'cortical_layer': 'N/A',
                      'hemisphere': hemisphere}
    # -- BrainLocation
    if brain_location not in reference.BrainLocation.proj():
        reference.BrainLocation.insert1(brain_location)
    # -- ActionLocation
    action_location = dict(brain_location,
                           coordinate_ref='bregma',
                           coordinate_ap=round(Decimal(coord_ap_ml_dv[0]), 2),
                           coordinate_ml=round(Decimal(coord_ap_ml_dv[1]), 2),
                           coordinate_dv=round(Decimal(coord_ap_ml_dv[2]), 2))
    if action_location not in reference.ActionLocation.proj():
        reference.ActionLocation.insert1(action_location)
    
    # -- Device
    stim_device = 'laser'  # hard-coded here..., could not find a more specific name from metadata
    if {'device_name': stim_device} not in stimulation.PhotoStimDevice.proj():
        stimulation.PhotoStimDevice.insert1({'device_name': stim_device, 'device_desc': devices[stim_device]})

    # -- PhotoStimulationInfo
    photim_stim_info = dict(action_location,
                            device_name=stim_device,
                            photo_stim_excitation_lambda=float(opto_excitation_lambda),
                            photo_stim_notes=(f'{opto_site_name} - {opto_descs}'))
    if photim_stim_info not in stimulation.PhotoStimulationInfo.proj():
        stimulation.PhotoStimulationInfo.insert1(photim_stim_info)

    # -- PhotoStimulation 
    # only 1 photostim per session, perform at the same time with session
    if dict({**subject_info, **session_info}, 
            photostim_datetime=session_info['session_time']) not in stimulation.PhotoStimulation.proj():
        photostim_data = nwb['stimulus']['presentation']['photostimulus']['data'].value
        photostim_timestamps = nwb['stimulus']['presentation']['photostimulus']['timestamps'].value
        stimulation.PhotoStimulation.insert1(dict({**subject_info, **session_info, **photim_stim_info},
                                                  photostim_datetime=session_info['session_time'],
                                                  photostim_timeseries=photostim_data,
                                                  photostim_start_time=photostim_timestamps[0],
                                                  photostim_sampling_rate=1/np.mean(np.diff(photostim_timestamps))), ignore_extra_fields=True)

    # -- finish manual ingestion for this file
    nwb.close()
