import os

import sys
from datetime import datetime
from dateutil.tz import tzlocal
import pytz
import re
import numpy as np
import json
import pandas as pd

from pipeline import (reference, subject, action, acquisition, behavior, ephys)
import pynwb
from pynwb import NWBFile, NWBHDF5IO


# ============================== SET CONSTANTS ==========================================
default_nwb_output_dir = os.path.join('/data', 'NWB 2.0')
zero_zero_time = datetime.strptime('00:00:00', '%H:%M:%S').time()  # no precise time available
hardware_filter = 'Bandpass filtered 300-6K Hz'
institution = 'Janelia Research Campus'


def export_to_nwb(session_key, nwb_output_dir=default_nwb_output_dir, save=False, overwrite=True):

    this_session = (acquisition.Session & session_key).fetch1()

    # ===============================================================================
    # ============================== META INFORMATION ===============================
    # ===============================================================================

    # -- NWB file - a NWB2.0 file for each session
    experimenter = (acquisition.Session.Experimenter & session_key).fetch1('experimenter')
    nwbfile = NWBFile(identifier='_'.join(
        [this_session['subject'],
         this_session['session_time'].strftime('%Y-%m-%d %H:%M:%S')]),
        related_publications='https://www.nature.com/articles/s41586-018-0633-x',
        experiment_description='Extracelluar recording in ALM',
        session_description='',
        session_start_time=this_session['session_time'],
        file_create_date=datetime.now(tzlocal()),
        experimenter=experimenter,
        institution=institution,
        keywords=['motor planning', 'anterior lateral cortex',
                  'ALM', 'Extracellular recording', 'optogenetics'])
    # -- subject
    subj = (subject.Subject & session_key).fetch1()

    nwbfile.subject = pynwb.file.Subject(
        subject_id=str(this_session['subject']),
        genotype=' x '.join((subject.Zygosity &
                             subj).fetch('allele')) \
                 if len(subject.Zygosity & subj) else 'unknown',
        sex=subj['sex'],
        species=subj['species'],
        date_of_birth=datetime.combine(subj['date_of_birth'], zero_zero_time) if subj['date_of_birth'] else None)
    # -- virus
    nwbfile.virus = json.dumps([{k: str(v) for k, v in virus_injection.items() if k not in subj}
                                for virus_injection in action.VirusInjection * reference.Virus & session_key])

    # ===============================================================================
    # ======================== EXTRACELLULAR & CLUSTERING ===========================
    # ===============================================================================

    """
    In the event of multiple probe recording (i.e. multiple probe insertions), the clustering results
    (and the associated units) are associated with the corresponding probe.
    Each probe insertion is associated with one ElectrodeConfiguration (which may define multiple electrode groups)
    """

    dj_insert_location = ephys.ProbeInsertion

    for probe_insertion in ephys.ProbeInsertion & session_key:
        probe = (reference.Probe & probe_insertion).fetch1()
        electrode_group = nwbfile.create_electrode_group(
                name=probe['probe_type'] + '_g1',
                description='N/A',
                device=nwbfile.create_device(name=probe['probe_type']),
                location=json.dumps({k: str(v) for k, v in (dj_insert_location & session_key).fetch1().items()
                                     if k not in dj_insert_location.primary_key}))

        for chn in (reference.Probe.Channel & probe).fetch(as_dict=True):
            nwbfile.add_electrode(
                id=chn['channel_id']-1,
                group=electrode_group,
                filtering=hardware_filter,
                imp=-1.,
                x=np.nan,
                y=np.nan,
                z=np.nan,
                location=(dj_insert_location & session_key).fetch1('brain_location'))


        # --- unit spike times ---
        nwbfile.add_unit_column(name='cell_type', description='cell type (e.g. fast spiking or pyramidal)')
        nwbfile.add_unit_column(name='sampling_rate', description='sampling rate of the waveform, Hz')

        spk_times_all = np.hstack((ephys.UnitSpikeTimes & probe_insertion).fetch('spike_times'))

        obs_min = np.min(spk_times_all)
        obs_max = np.max(spk_times_all)

        for unit in (ephys.UnitSpikeTimes & probe_insertion).fetch(as_dict=True):
            nwbfile.add_unit(id=unit['unit_id'],
                             electrodes=[unit['channel']-1],
                             electrode_group=electrode_group,
                             cell_type=unit['unit_cell_type'],
                             spike_times=unit['spike_times'],
                             obs_intervals=np.array([[obs_min - 0.001, obs_max + 0.001]]),
                             waveform_mean=np.mean(unit['spike_waveform'], axis=0),
                             waveform_sd=np.std(unit['spike_waveform'], axis=0),
                             sampling_rate=20000)

    # ===============================================================================
    # ============================= PHOTO-STIMULATION ===============================
    # ===============================================================================
    stim_sites = {}
    for photostim in acquisition.PhotoStim * reference.BrainLocation & session_key:

        stim_device = (nwbfile.get_device(photostim['photo_stim_method'])
                       if photostim['photo_stim_method'] in nwbfile.devices
                       else nwbfile.create_device(name=photostim['photo_stim_method']))

        stim_site = pynwb.ogen.OptogeneticStimulusSite(
            name=photostim['brain_location'],
            device=stim_device,
            excitation_lambda=float(photostim['photo_stim_wavelength']),
            location=json.dumps({k: str(v) for k, v in photostim.items()
                                if k in acquisition.PhotoStim.heading.names and k not in acquisition.PhotoStim.primary_key + ['photo_stim_method', 'photo_stim_wavelength']}),
            description='')
        nwbfile.add_ogen_site(stim_site)

    # ===============================================================================
    # =============================== BEHAVIOR TRIALS ===============================
    # ===============================================================================

    # =============== TrialSet ====================
    # NWB 'trial' (of type dynamic table) by default comes with three mandatory attributes: 'start_time' and 'stop_time'
    # Other trial-related information needs to be added in to the trial-table as additional columns (with column name
    # and column description)

    dj_trial = acquisition.Session * behavior.TrialSet.Trial
    skip_adding_columns = acquisition.Session.primary_key + \
        ['trial_id', 'trial_start_idx', 'trial_end_idx', 'trial_start_time', 'session_note']

    if behavior.TrialSet.Trial & session_key:
        # Get trial descriptors from TrialSet.Trial and TrialStimInfo
        trial_columns = [{'name': tag.replace('trial_', ''),
                          'description': re.sub('\s+:|\s+', ' ', re.search(
                              f'(?<={tag})(.*)', str(dj_trial.heading)).group()).strip()}
                         for tag in dj_trial.heading.names
                         if tag not in skip_adding_columns]


        # Add new table columns to nwb trial-table for trial-label
        for c in trial_columns:
            nwbfile.add_trial_column(**c)

        # Add entry to the trial-table
        for trial in (dj_trial & session_key).fetch(as_dict=True):
            trial['start_time'] = float(trial['trial_start_time'])
            trial['stop_time'] = float(trial['trial_start_time']) + 5.0
            trial['trial_pole_in_time'] = trial['start_time'] + trial['trial_pole_in_time']
            trial['trial_pole_out_time'] = trial['start_time'] + trial['trial_pole_out_time']
            trial['trial_cue_time'] = trial['start_time'] + trial['trial_cue_time']
            [trial.pop(k) for k in skip_adding_columns]
            for k in trial.keys():
                if 'trial_' in k:
                    trial[k.replace('trial_', '')] = trial.pop(k)
            nwbfile.add_trial(**trial)


    # =============== Write NWB 2.0 file ===============
    if save:
        save_file_name = ''.join([nwbfile.identifier, '.nwb'])
        if not os.path.exists(nwb_output_dir):
            os.makedirs(nwb_output_dir)
        if not overwrite and os.path.exists(os.path.join(nwb_output_dir, save_file_name)):
            return nwbfile
        with NWBHDF5IO(os.path.join(nwb_output_dir, save_file_name), mode='w') as io:
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
