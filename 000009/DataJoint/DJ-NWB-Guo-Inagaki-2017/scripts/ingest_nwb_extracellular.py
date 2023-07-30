# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 16:22:42 2018

@author: thinh
"""
import os
import re
import pathlib
import datajoint as dj

import h5py as h5
import numpy as np
from decimal import Decimal

from pipeline import (reference, subject, acquisition, stimulation, analysis,
                      intracellular, extracellular, behavior, utilities)

# ================== Dataset ==================
path = pathlib.Path(dj.config['custom'].get('extracellular_directory')).as_posix()
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
    # ==================== Subject ====================
    subject_info = {c: nwb['general']['subject'][c].value.decode('UTF-8')
                    for c in ('subject_id', 'description', 'sex', 'species', 'age', 'genotype')}
    # force subject_id to be lower-case for consistency
    subject_info['subject_id'] = subject_info['subject_id'].lower()

    # dob and sex
    subject_info['sex'] = subject_info['sex'][0].upper()
    dob_str = re.search('(?<=dateOfBirth:\s)(.*)(?=\n)', subject_info['description'])
    if utilities.parse_prefix(dob_str.group()) is not None:
        subject_info['date_of_birth'] = utilities.parse_prefix(dob_str.group())
    
    # allele
    allele_str = re.search('(?<=animalStrain:\s)(.*)', subject_info['description']).group() # extract the information related to animal allele
    allele_dict = {alias.lower(): allele for alias, allele in zip(
        subject.AlleleAlias.fetch('allele_alias', 'allele'))}
    regex_str = '|'.join([re.escape(alias) for alias in allele_dict.keys()])
    alleles = [allele_dict[s.lower()] for s in re.findall(regex_str, allele_str, re.I)]
    # source
    source_str = re.search('(?<=animalSource:\s)(.*)', subject_info['description']).group()  # extract the information related to animal allele
    source_dict = {alias.lower(): source for alias, source in zip(
        reference.AnimalSourceAlias.fetch('animal_source_alias', 'animal_source'))}
    regex_str = '|'.join([re.escape(alias) for alias in source_dict.keys()])
    subject_info['animal_source'] = source_dict[re.search(regex_str, source_str, re.I).group().lower()] if re.search(regex_str, source_str, re.I) else 'N/A'

    if subject_info not in subject.Subject.proj():
        with subject.Subject.connection.transaction:
            subject.Subject.insert1(subject_info, ignore_extra_fields=True)
            subject.Subject.Allele.insert((dict(subject_info, allele = k)
                                           for k in alleles), ignore_extra_fields = True)

    # ==================== session ====================
    # -- session_time
    session_time = utilities.parse_prefix(nwb['session_start_time'].value)  # info here is incorrect (see identifier)
    # due to incorrect info in "session_start_time" - temporary fix: use info in 'identifier'
    session_time = re.split(';\s?', nwb['identifier'].value)[-1].replace('T', ' ')
    session_time = utilities.parse_prefix(session_time)

    if session_time is not None:
        session_info = dict(
            experiment_description=nwb['general']['experiment_description'].value,
            institution=nwb['general']['institution'].value,
            related_publications=nwb['general']['related_publications'].value.decode('UTF-8'),
            surgery=nwb['general']['surgery'].value.decode('UTF-8'),
            identifier=nwb['identifier'].value,
            nwb_version=nwb['nwb_version'].value,
            session_note=nwb['session_description'].value,
            session_time=session_time)

        experimenters = nwb['general']['experimenter'].value
        # experimenter and experiment type (possible multiple experimenters or types)
        experimenters = [experimenters] if np.array(
            experimenters).size <= 1 else experimenters  # in case there's only 1 experimenter

        reference.Experimenter.insert(({'experimenter': k} for k in experimenters
                                       if {'experimenter': k} not in reference.Experimenter))

        with acquisition.Session.connection.transaction:
            if dict(subject_info, session_time = session_time) not in acquisition.Session.proj():
                acquisition.Session.insert1({**subject_info, **session_info}, ignore_extra_fields=True)
                acquisition.Session.Experimenter.insert((dict({**subject_info, **session_info}, experimenter=k)
                                                         for k in experimenters), ignore_extra_fields=True)
                # there is still the ExperimentType part table here...
            print(f'Creating Session - Subject: {subject_info["subject_id"]} - Date: {session_info["session_time"]}')

    # ==================== Trials ====================
    trial_key = {'subject_id': subject_info["subject_id"], 'session_time': session_info["session_time"]}
    # map the hardcoded trial description (from 'reference.TrialType')
    trial_type_choices = {'L': 'lick left',
                          'R': 'lick right'}
    # map the hardcoded trial description (from 'reference.TrialResponse')
    trial_resp_choices = {'Hit': 'correct',
                          'Err': 'incorrect',
                          'NoLick': 'no response',
                          'LickEarly': 'early lick'}
    photostim_period_choices = {1: 'sample', 2: 'delay', 3: 'response'}

    # -- read trial-related info -- nwb['epochs'], nwb['analysis'], nwb['stimulus']['presentation'])
    cue_duration = 0.1  # hard-coded the fact that an auditory cue last 0.1 second
    trial_details = dict(trial_names=[t for t in nwb['epochs']],
                         tags=[nwb['epochs'][t]['tags'].value for t in nwb['epochs']],
                         start_times=[nwb['epochs'][t]['start_time'].value for t in nwb['epochs']],
                         stop_times=[nwb['epochs'][t]['stop_time'].value for t in nwb['epochs']],
                         trial_type_string=np.array(nwb['analysis']['trial_type_string']),
                         trial_type_mat=np.array(nwb['analysis']['trial_type_mat']),
                         cue_start_times=np.array(nwb['stimulus']['presentation']['auditory_cue']['timestamps']),
                         cue_end_times=np.array(nwb['stimulus']['presentation']['auditory_cue']['timestamps']) + cue_duration,  # hard-coded cue_end time here
                         pole_in_times=np.array(nwb['stimulus']['presentation']['pole_in']['timestamps']),
                         pole_out_times=np.array(nwb['stimulus']['presentation']['pole_out']['timestamps']))

    # form new key-values pair and insert key
    trial_key['trial_counts'] = len(trial_details['trial_names'])
    if trial_key not in acquisition.TrialSet.proj():
        acquisition.TrialSet.insert1(trial_key, allow_direct_insert=True)
        print(f'Inserted trial set for: Subject: {subject_info["subject_id"]} - Date: {session_info["session_time"]}')
        print('Inserting trial ID: ', end="")
        # loop through each trial and insert
        for idx, trial_id in enumerate(trial_details['trial_names']):
            trial_id = int(re.search('(\d+)', trial_id).group())
            trial_key['trial_id'] = trial_id
            # -- start/stop time
            trial_key['start_time'] = trial_details['start_times'][idx]
            trial_key['stop_time'] = trial_details['stop_times'][idx]
            # ======== Now add trial descriptors ====
            # search through all keyword in trial descriptor tags (keywords are not in fixed order)
            tag_key = {}
            tag_key['trial_is_good'] = False
            tag_key['trial_stim_present'] = True
            tag_key['trial_type'] = 'non-performing'
            tag_key['trial_response'], tag_key['photo_stim_type'] = 'N/A', 'N/A'
            for tag in trial_details['tags'][idx]:
                # good/bad
                if not tag_key['trial_is_good']:
                    tag_key['trial_is_good'] = (re.match('good', tag, re.I) is not None)
                # stim/no-stim
                if tag_key['trial_stim_present']:
                    tag_key['trial_stim_present'] = (re.match('non-stimulation', tag, re.I) is None)
                # trial type: left/right lick
                if tag_key['trial_type'] == 'non-performing':
                    m = re.match('Hit|Err|NoLick', tag)
                    tag_key['trial_type'] = 'non-performing' if (m is None) else trial_type_choices[tag[m.end()]]
                # trial response type: correct, incorrect, early lick, no response
                if tag_key['trial_response'] == 'N/A' or tag_key['trial_response'] != 'early lick':
                    m = re.match('Hit|Err|NoLick|LickEarly', tag)
                    if m: m.group()
                    tag_key['trial_response'] = trial_resp_choices[m.group()] if m else tag_key['trial_response']
                # photo stim type: stimulation, inhibition, or N/A (for non-stim trial)
                if tag_key['photo_stim_type'] == 'N/A':
                    m = re.match('PhotoStimulation|PhotoInhibition', tag, re.I)
                    tag_key['photo_stim_type'] = 'N/A' if (m is None) else m.group().replace('Photo','').lower()
            # insert
            acquisition.TrialSet.Trial.insert1({**trial_key, **tag_key},
                                               ignore_extra_fields=True, allow_direct_insert=True)
            # ======== Now add trial event timing to the TrialInfo part table ====
            # -- events timing
            acquisition.TrialSet.EventTime.insert((dict(trial_key, trial_event=k, event_time=trial_details[e][idx])
                                                    for k, e in zip(('trial_start', 'trial_stop', 'cue_start',
                                                                     'cue_end', 'pole_in', 'pole_out'),
                                                                    ('start_times', 'stop_times', 'cue_start_times',
                                                                     'cue_end_times', 'pole_in_times', 'pole_out_times'))),
                                                   ignore_extra_fields=True, allow_direct_insert=True)

            # ======== Now add trial stimulation descriptors to the TrialPhotoStimInfo table ====
            trial_key['photo_stim_period'] = ('N/A' if trial_details['trial_type_mat'][-5, idx] == 0
                                              else photostim_period_choices[trial_details['trial_type_mat'][-5, idx]])
            trial_key['photo_stim_power'] = trial_details['trial_type_mat'][-4, idx]
            trial_key['photo_loc_galvo_x'] = trial_details['trial_type_mat'][-3, idx]
            trial_key['photo_loc_galvo_y'] = trial_details['trial_type_mat'][-2, idx]
            trial_key['photo_loc_galvo_z'] = trial_details['trial_type_mat'][-1, idx]
            # insert
            stimulation.TrialPhotoStimInfo.insert1(trial_key, ignore_extra_fields=True, allow_direct_insert=True)
            print(f'{trial_id} ', end="")
        print('')

    # ==================== Extracellular ====================
    # -- read data - devices
    device_names = list(nwb['general']['devices'])
    # -- read data - electrodes
    electrodes = nwb['general']['extracellular_ephys']['electrodes']
    # get probe placement from 0th electrode (should be the same for all electrodes)
    probe_placement_brain_loc = electrodes[0][5].decode('UTF-8')
    probe_placement_brain_loc = re.search("(?<=\[\')(.*)(?=\'\])", probe_placement_brain_loc).group()

    # -- Probe
    if {'probe_name': device_names[0], 'channel_counts': len(electrodes)} not in reference.Probe.proj():
        reference.Probe.insert1(
                {'probe_name': device_names[0],
                 'channel_counts': len(electrodes)})
        reference.Probe.Channel.insert((
            {'probe_name': device_names[0], 'channel_counts': len(electrodes), 'channel_id': electrode[0],
             'channel_x_pos': electrode[1], 'channel_y_pos': electrode[2], 'channel_z_pos': electrode[3],
             'shank_id' : int(re.search('\d+', electrode[-2].decode('UTF-8')).group())}
            for electrode in electrodes))

    # -- BrainLocation
    # hemisphere: left-hemisphere is ipsi, so anything contra is right
    brain_region, hemisphere = utilities.get_brain_hemisphere(probe_placement_brain_loc)
    brain_location = {'brain_region': brain_region,
                      'brain_subregion': 'N/A',
                      'cortical_layer': 'N/A',
                      'hemisphere': hemisphere}
    # -- BrainLocation
    if brain_location not in reference.BrainLocation.proj():
        reference.BrainLocation.insert1(brain_location)
    # -- ActionLocation
    ground_coordinates = nwb['general']['extracellular_ephys']['ground_coordinates'].value  # using 'ground_coordinates' here as the x, y, z for where the probe is placed in the brain, TODO double check if this is correct
    action_location = dict(brain_location,
                           coordinate_ref='bregma',
                           coordinate_ap=round(Decimal(str(ground_coordinates[0])), 2),
                           coordinate_ml=round(Decimal(str(ground_coordinates[1])), 2),
                           coordinate_dv=round(Decimal(str(ground_coordinates[2])), 2))
    if action_location not in reference.ActionLocation.proj():
        reference.ActionLocation.insert1(action_location)

    # -- ProbeInsertion
    probe_insertion = dict({**subject_info, **session_info, **action_location},
                           probe_name=device_names[0], channel_counts=len(electrodes))

    if probe_insertion not in extracellular.ProbeInsertion.proj():
        extracellular.ProbeInsertion.insert1(probe_insertion, ignore_extra_fields=True)

    # ==================== Photo stimulation ====================
    # -- Device
    stim_device = 'laser'  # hard-coded here..., could not find a more specific name from metadata

    # -- read data - optogenetics
    opto_site_name = list(nwb['general']['optogenetics'].keys())[0]
    opto_descs = nwb['general']['optogenetics'][opto_site_name]['description'].value.decode('UTF-8')
    opto_excitation_lambda = nwb['general']['optogenetics'][opto_site_name]['excitation_lambda'].value.decode('UTF-8')
    opto_location = nwb['general']['optogenetics'][opto_site_name]['location'].value.decode('UTF-8')
    opto_stimulation_method = nwb['general']['optogenetics'][opto_site_name]['stimulation_method'].value.decode('UTF-8')

    brain_region = re.search('(?<=atlas location:\s)(.*)', opto_location).group()
    
    # hemisphere: left-hemisphere is ipsi, so anything contra is right
    brain_region, hemisphere = utilities.get_brain_hemisphere(brain_region)
    
    # if no brain region (NA, or N/A, or ' '), skip photostim insert
    if re.search('\s+|N/?A', brain_region) is None:

        # -- BrainLocation
        brain_location = {'brain_region': brain_region,
                          'brain_subregion': 'N/A',
                          'cortical_layer': 'N/A',
                          'hemisphere': hemisphere}
        if brain_location not in reference.BrainLocation.proj():
            reference.BrainLocation.insert1(brain_location)
        # -- ActionLocation
        coord_ap_ml_dv = re.search('(?<=\[)(.*)(?=\])', opto_location).group()
        coord_ap_ml_dv = re.split(',', coord_ap_ml_dv)
        action_location = dict(brain_location,
                               coordinate_ref='bregma',
                               coordinate_ap=round(Decimal(coord_ap_ml_dv[0]), 2),
                               coordinate_ml=round(Decimal(coord_ap_ml_dv[1]), 2),
                               coordinate_dv=round(Decimal(coord_ap_ml_dv[2]), 2))
        if action_location not in reference.ActionLocation.proj():
            reference.ActionLocation.insert1(action_location)

        if {'device_name': stim_device} not in stimulation.PhotoStimDevice.proj():
            stimulation.PhotoStimDevice.insert1({'device_name': stim_device})

        # -- PhotoStimulationInfo
        photim_stim_info = dict(action_location,
                                device_name=stim_device,
                                photo_stim_excitation_lambda=float(opto_excitation_lambda),
                                photo_stim_notes=(f'{opto_site_name} - {opto_descs}'))
        if photim_stim_info not in stimulation.PhotoStimulationInfo.proj():
            stimulation.PhotoStimulationInfo.insert1(photim_stim_info)
    
        # -- PhotoStimulation
        if dict({**subject_info, **session_info},
                photostim_datetime = session_info['session_time']) not in stimulation.PhotoStimulation.proj():
            # only 1 photostim per session, perform at the same time with session
            photostim_data = nwb['stimulus']['presentation']['photostimulus_1']['data'].value
            photostim_timestamps = nwb['stimulus']['presentation']['photostimulus_1']['timestamps'].value
            # if the dataset does not contain photostim timeseries set to None
            photostim_data = None if not isinstance(photostim_data, np.ndarray) else photostim_data
            photostim_timestamps = None if not isinstance(photostim_timestamps, np.ndarray) else photostim_timestamps
            photostim_start_time = None if not isinstance(photostim_timestamps, np.ndarray) else photostim_timestamps[0]
            photostim_sampling_rate = (None if not isinstance(photostim_timestamps, np.ndarray)
                                       else 1/np.mean(np.diff(photostim_timestamps)))
            stimulation.PhotoStimulation.insert1(dict({**subject_info, **session_info, **photim_stim_info},
                                                      photostim_datetime=session_info['session_time'],
                                                      photostim_timeseries=photostim_data,
                                                      photostim_start_time=photostim_start_time,
                                                      photostim_sampling_rate=photostim_sampling_rate),
                                                 ignore_extra_fields = True)

    # -- finish manual ingestion for this file
    nwb.close()
