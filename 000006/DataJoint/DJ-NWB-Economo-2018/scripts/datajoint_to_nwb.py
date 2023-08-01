#!/usr/bin/env python3
import os

import sys
from datetime import datetime
from dateutil.tz import tzlocal
import re
import numpy as np
import warnings

from pipeline import (reference, subject, acquisition, analysis,
                      extracellular, behavior, utilities)
import pynwb
from pynwb import NWBFile, NWBHDF5IO

warnings.filterwarnings('ignore', module='pynwb')

# ============================== SET CONSTANTS ==========================================
default_nwb_output_dir = os.path.join('data', 'NWB 2.0')
zero_zero_time = datetime.strptime('00:00:00', '%H:%M:%S').time()  # no precise time available
hardware_filter = 'Bandpass filtered 300-6K Hz'
institution = 'Janelia Research Campus'
related_publications = 'doi:10.1038/s41586-018-0642-9'

# experiment description and keywords - from the abstract
experiment_description = 'Extracellular electrophysiology recordings performed on mouse anterior lateral motor cortex (ALM) in delay response task. Neural activity from two neuron populations, pyramidal track upper and lower, were characterized, in relation to movement execution.'
keywords = ['motor planning', 'premotor cortex', 'preparatory activity', 'extracellular electrophysiology']


def export_to_nwb(session_key, nwb_output_dir=default_nwb_output_dir, save=False, overwrite=True):
    this_session = (acquisition.Session & session_key).fetch1()

    identifier = '_'.join([this_session['subject_id'],
                           this_session['session_time'].strftime('%Y-%m-%d'),
                           str(this_session['session_id'])])
    # =============== General ====================
    # -- NWB file - a NWB2.0 file for each session
    nwbfile = NWBFile(
        session_description=this_session['session_note'],
        identifier=identifier,
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
        sex=subj['sex'],
        species=subj['species'])

    # =============== Extracellular ====================
    probe_insertion = ((extracellular.ProbeInsertion & session_key).fetch1()
                       if extracellular.ProbeInsertion & session_key
                       else None)
    if probe_insertion:
        probe = nwbfile.create_device(name = probe_insertion['probe_name'])
        electrode_group = nwbfile.create_electrode_group(
            name='; '.join([f'{probe_insertion["probe_name"]}: {str(probe_insertion["channel_counts"])}']),
            description='N/A',
            device=probe,
            location='; '.join([f'{k}: {str(v)}' for k, v in
                                  (reference.BrainLocation & probe_insertion).fetch1().items()]))

        for chn in (reference.Probe.Channel & probe_insertion).fetch(as_dict=True):
            nwbfile.add_electrode(id=chn['channel_id'],
                                  group=electrode_group,
                                  filtering=hardware_filter,
                                  imp=np.nan,
                                  x=np.nan,  # not available from data
                                  y=np.nan,  # not available from data
                                  z=np.nan,  # not available from data
                                  location=electrode_group.location)

        # --- unit spike times ---
        nwbfile.add_unit_column(name='depth', description='depth this unit (um)')
        nwbfile.add_unit_column(name='quality', description='quality of the spike sorted unit (e.g. excellent, good, poor, fair, etc.)')
        nwbfile.add_unit_column(name='cell_type', description='cell type (e.g. PTlower, PTupper)')

        for unit in (extracellular.UnitSpikeTimes & probe_insertion).fetch(as_dict=True):
            # make an electrode table region (which electrode(s) is this unit coming from)
            unit_chn = unit['channel_id'] if isinstance(unit['channel_id'], np.ndarray) else [unit['channel_id']]

            nwbfile.add_unit(id=unit['unit_id'],
                             electrodes=np.where(np.in1d(np.array(nwbfile.electrodes.id.data), unit_chn))[0],
                             depth=unit['unit_depth'],
                             quality=unit['unit_quality'],
                             cell_type=unit['unit_cell_type'],
                             spike_times=unit['spike_times'])

    # =============== Behavior ====================
    behavior_data = ((behavior.LickTimes & session_key).fetch1()
                     if behavior.LickTimes & session_key
                     else None)
    if behavior_data:
        behav_acq = pynwb.behavior.BehavioralEvents(name='lick_times')
        nwbfile.add_acquisition(behav_acq)
        [behavior_data.pop(k) for k in behavior.LickTimes.primary_key]
        for b_k, b_v in behavior_data.items():
            behav_acq.create_timeseries(name=b_k,
                                        unit='a.u.',
                                        conversion=1.0,
                                        data=np.full_like(b_v, 1).astype(bool),
                                        timestamps=b_v)

    # =============== TrialSet ====================
    # NWB 'trial' (of type dynamic table) by default comes with three mandatory attributes:
    #                                                                       'id', 'start_time' and 'stop_time'.
    # Other trial-related information needs to be added in to the trial-table as additional columns (with column name
    # and column description)

    # adjust trial event times to be relative to session's start time
    q_trial_event = (acquisition.TrialSet.EventTime * acquisition.TrialSet.Trial.proj('start_time')).proj(
            event_time='event_time + start_time')

    if acquisition.TrialSet & session_key:
        # Get trial descriptors from TrialSet.Trial and TrialStimInfo
        trial_columns = [{'name': tag.replace('trial_', ''),
                          'description': re.search(
                              f'(?<={tag})(.*)#(.*)', str(acquisition.TrialSet.Trial.heading)).groups()[-1].strip()}
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
            events = dict(zip(*(q_trial_event & trial & [{'trial_event': e}
                                                         for e in trial_events]).fetch('trial_event', 'event_time')))

            trial_tag_value = {**trial, **events, 'stop_time': np.nan}  # No stop_time available for this dataset

            trial_tag_value['id'] = trial_tag_value['trial_id']  # rename 'trial_id' to 'id'
            # convert None to np.nan since nwb fields does not take None
            for k, v in trial_tag_value.items():
                trial_tag_value[k] = v if v is not None else np.nan
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
