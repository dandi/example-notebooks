#!/usr/bin/env python3
import os

import sys
from datetime import datetime
from dateutil.tz import tzlocal
import pytz
import re
import numpy as np
import pandas as pd
import tqdm
import warnings

from pipeline import (reference, subject, acquisition, stimulation, analysis, virus,
                      intracellular, behavior, utilities)
import pynwb
from pynwb import NWBFile, NWBHDF5IO

warnings.filterwarnings('ignore', module='pynwb')

# ============================== SET CONSTANTS ==========================================
# Each NWBFile represent a session, thus for every session in acquisition.Session, we build one NWBFile
default_nwb_output_dir = os.path.join('data', 'NWB 2.0')
institution = 'Janelia Research Campus'
related_publications = '10.7554/eLife.06619'

# experiment description and keywords - from the abstract
experiment_description = 'Intracellular and extracellular electrophysiology recordings performed on mouse barrel cortex in object locating task, where whisker movements and contacts with object were tracked to the milisecond precision.'
keywords = ['barrel cortex', 'whiskers', 'extracellular electrophysiology', 'intracellular electrophysiology']


def export_to_nwb(session_key, nwb_output_dir=default_nwb_output_dir, save=False, overwrite=True):
    this_session = (acquisition.Session & session_key).fetch1()
    # =============== General ====================
    # -- NWB file - a NWB2.0 file for each session
    nwbfile = NWBFile(
        session_description=this_session['session_note'],
        identifier='_'.join([this_session['subject_id'],
                             this_session['session_time'].strftime('%Y-%m-%d'),
                             this_session['session_id']]),
        session_start_time=this_session['session_time'],
        file_create_date=datetime.now(tzlocal()),
        experimenter='; '.join((acquisition.Session.Experimenter & session_key).fetch('experimenter')),
        institution=institution,
        experiment_description=experiment_description,
        related_publications=related_publications,
        keywords=keywords)
    # -- subject
    subj = (subject.Subject & session_key).fetch1()
    nwbfile.subject = pynwb.file.Subject(
        subject_id=this_session['subject_id'],
        description=subj['subject_description'],
        genotype= ' x '.join((subject.Subject.Allele & session_key).fetch('allele')),
        sex=subj['sex'],
        species=subj['species'])
    # =============== Intracellular ====================
    cell = ((intracellular.Cell & session_key).fetch1()
            if len(intracellular.Cell & session_key) == 1
            else None)
    if cell:
        # metadata
        whole_cell_device = nwbfile.create_device(name=cell['device_name'])
        ic_electrode = nwbfile.create_ic_electrode(
            name=cell['cell_id'],
            device=whole_cell_device,
            description='N/A',
            filtering='N/A',
            location='; '.join([f'{k}: {str(v)}'
                                for k, v in dict((reference.BrainLocation & cell).fetch1(),
                                                 depth=cell['recording_depth']).items()]))
        # acquisition - membrane potential
        mp, mp_timestamps = (intracellular.MembranePotential & cell).fetch1(
            'membrane_potential', 'membrane_potential_timestamps')
        nwbfile.add_acquisition(pynwb.icephys.PatchClampSeries(name='PatchClampSeries',
                                                               electrode=ic_electrode,
                                                               unit='mV',
                                                               conversion=1e-3,
                                                               gain=1.0,
                                                               data=mp,
                                                               timestamps=mp_timestamps))

        # acquisition - spike train
        spk, spk_timestamps = (intracellular.SpikeTrain & cell).fetch1(
            'spike_train', 'spike_timestamps')
        nwbfile.add_acquisition(pynwb.icephys.PatchClampSeries(name='SpikeTrain',
                                                               electrode=ic_electrode,
                                                               unit='a.u.',
                                                               conversion=1e1,
                                                               gain=1.0,
                                                               data=spk,
                                                               timestamps=spk_timestamps))

    # =============== Behavior ====================
    behavior_data = ((behavior.Behavior & session_key).fetch1()
                       if len(behavior.Behavior & session_key) == 1
                       else None)
    if behavior_data:
        behav_acq = pynwb.behavior.BehavioralTimeSeries(name='behavior')
        nwbfile.add_acquisition(behav_acq)
        [behavior_data.pop(k) for k in behavior.Behavior.primary_key]
        timestamps = behavior_data.pop('behavior_timestamps')

        # get behavior data description from the comments of table definition
        behavior_descriptions = {attr: re.search(f'(?<={attr})(.*)#(.*)',
                                                 str(behavior.Behavior.heading)).groups()[-1].strip()
                                 for attr in behavior_data}

        for b_k, b_v in behavior_data.items():
            behav_acq.create_timeseries(name=b_k,
                                        description=behavior_descriptions[b_k],
                                        unit='a.u.',
                                        conversion=1.0,
                                        data=b_v,
                                        timestamps=timestamps)

    # =============== Photostimulation ====================
    photostim = ((stimulation.PhotoStimulation & session_key).fetch1()
                       if len(stimulation.PhotoStimulation & session_key) == 1
                       else None)
    if photostim:
        photostim_device = (stimulation.PhotoStimDevice & photostim).fetch1()
        stim_device = nwbfile.create_device(name=photostim_device['device_name'])
        stim_site = pynwb.ogen.OptogeneticStimulusSite(
            name='-'.join([photostim['hemisphere'], photostim['brain_region']]),
            device=stim_device,
            excitation_lambda=float((stimulation.PhotoStimulationProtocol & photostim).fetch1('photo_stim_excitation_lambda')),
            location='; '.join([f'{k}: {str(v)}' for k, v in
                                (reference.ActionLocation & photostim).fetch1().items()]),
            description=(stimulation.PhotoStimulationProtocol & photostim).fetch1('photo_stim_notes'))
        nwbfile.add_ogen_site(stim_site)

        if photostim['photostim_timeseries'] is not None:
            nwbfile.add_stimulus(pynwb.ogen.OptogeneticSeries(
                name='_'.join(['photostim_on', photostim['photostim_datetime'].strftime('%Y-%m-%d_%H-%M-%S')]),
                site=stim_site,
                resolution=0.0,
                conversion=1e-3,
                data=photostim['photostim_timeseries'],
                starting_time=photostim['photostim_start_time'],
                rate=photostim['photostim_sampling_rate']))

    # =============== TrialSet ====================
    # NWB 'trial' (of type dynamic table) by default comes with three mandatory attributes:
    #                                                                       'id', 'start_time' and 'stop_time'.
    # Other trial-related information needs to be added in to the trial-table as additional columns (with column name
    # and column description)
    if len((acquisition.TrialSet & session_key).fetch()) == 1:
        # Get trial descriptors from TrialSet.Trial and TrialStimInfo - remove '_trial' prefix (if any)
        trial_columns = [{'name': tag.replace('trial_', ''),
                          'description': re.search(
                              f'(?<={tag})(.*)#(.*)',
                              str((acquisition.TrialSet.Trial
                                   * stimulation.TrialPhotoStimInfo).heading)).groups()[-1].strip()}
                         for tag in acquisition.TrialSet.Trial.heading.names
                         if tag not in acquisition.TrialSet.Trial.primary_key + ['start_time', 'stop_time']]

        # Trial Events - discard 'trial_start' and 'trial_stop' as we already have start_time and stop_time
        # also add `_time` suffix to all events
        trial_events = set(((acquisition.TrialSet.EventTime & session_key)
                            - [{'trial_event': 'trial_start'}, {'trial_event': 'trial_stop'}]).fetch('trial_event'))
        event_names = [{'name': e + '_time', 'description': d}
                       for e, d in zip(*(reference.ExperimentalEvent & [{'event': k}
                                                                        for k in trial_events]).fetch('event',
                                                                                                      'description'))]
        # Add new table columns to nwb trial-table for trial-label
        for c in trial_columns + event_names:
            nwbfile.add_trial_column(**c)

        # Add entry to the trial-table
        for trial in (acquisition.TrialSet.Trial & session_key).fetch(as_dict=True):
            events = dict(zip(*(acquisition.TrialSet.EventTime & trial
                                & [{'trial_event': e} for e in trial_events]).fetch('trial_event', 'event_time')))
            # shift event times to be relative to session_start (currently relative to trial_start)
            events = {k: v + trial['start_time'] for k, v in events.items()}

            trial_tag_value = {**trial, **events}
            # rename 'trial_id' to 'id'
            trial_tag_value['id'] = trial_tag_value['trial_id']
            [trial_tag_value.pop(k) for k in acquisition.TrialSet.Trial.primary_key]

            # Final tweaks: i) add '_time' suffix and ii) remove 'trial_' prefix
            events = {k + '_time': trial_tag_value.pop(k) for k in events}
            trial_attrs = {k.replace('trial_', ''): trial_tag_value.pop(k)
                           for k in [n for n in trial_tag_value if n.startswith('trial_')]}

            nwbfile.add_trial(**trial_tag_value, **events, **trial_attrs)

        # =============== Write NWB 2.0 file ===============
        if save:
            save_file_name = ''.join([nwbfile.identifier, '.nwb'])
            if not os.path.exists(nwb_output_dir):
                os.makedirs(nwb_output_dir)
            if not overwrite and os.path.exists(os.path.join(nwb_output_dir, save_file_name)):
                return nwbfile
            with NWBHDF5IO(os.path.join(nwb_output_dir, save_file_name), mode = 'w') as io:
                io.write(nwbfile)
                print(f'Write NWB 2.0 file: {save_file_name}')

        return nwbfile


# ============================== EXPORT ALL ==========================================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        nwb_outdir = sys.argv[1]
    else:
        nwb_outdir = default_nwb_output_dir

    for skey in acquisition.Session.fetch('KEY'):
        export_to_nwb(skey, nwb_output_dir=nwb_outdir, save=True)
