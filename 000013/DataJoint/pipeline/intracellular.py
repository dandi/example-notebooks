'''
Schema of intracellular information.
'''
import re
import os
import sys
from datetime import datetime

import numpy as np
import scipy.io as sio
from scipy import sparse
import datajoint as dj

from . import reference, utilities, acquisition, analysis

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'intracellular')

data_dir = dj.config['custom'].get('data_directory')


@schema
class Cell(dj.Manual):
    definition = """ # A cell undergone intracellular recording in this session
    -> acquisition.Session
    cell_id: varchar(36) # a string identifying the cell in which this intracellular recording is concerning
    ---
    cell_type: enum('excitatory', 'inhibitory', 'N/A')
    -> reference.BrainLocation
    recording_depth: decimal(6,2)  # (um)
    -> reference.WholeCellDevice
    """


@schema
class MembranePotential(dj.Imported):
    definition = """ # Membrane potential recording from a cell
    -> Cell
    ---
    membrane_potential: longblob  # (mV)
    membrane_potential_timestamps: longblob  # (s)
    """

    def make(self, key):
        sess_data_file = utilities.find_session_matched_matfile(key)
        if sess_data_file is None:
            raise FileNotFoundError(f'Intracellular import failed: ({key["subject_id"]} - {key["session_time"]})')
        sess_data = sio.loadmat(sess_data_file, struct_as_record = False, squeeze_me = True)['c']
        time_conversion_factor = utilities.time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.timeSeriesArrayHash.value[1].timeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing
        ephys_data = sess_data.timeSeriesArrayHash.value[1].valueMatrix * time_conversion_factor
        time_stamps = sess_data.timeSeriesArrayHash.value[1].time * time_conversion_factor

        key['membrane_potential'] = (ephys_data[0, :]
                                     if not isinstance(ephys_data[0, :], sparse.csc_matrix)
                                     else np.asarray(ephys_data[0, :].todense()).flatten())
        key['membrane_potential_timestamps'] = time_stamps

        self.insert1(key)
        print(f'Inserted voltage data for session: {key["session_id"]}')


@schema
class SpikeTrain(dj.Imported):
    definition = """ # Spike-train recording of this Cell
    -> Cell
    ---
    spike_train: longblob
    spike_timestamps: longblob  # (s)
    """

    def make(self, key):
        sess_data_file = utilities.find_session_matched_matfile(key)
        if sess_data_file is None:
            raise FileNotFoundError(f'Intracellular import failed: ({key["subject_id"]} - {key["session_time"]})')
        sess_data = sio.loadmat(sess_data_file, struct_as_record = False, squeeze_me = True)['c']
        time_conversion_factor = utilities.time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.timeSeriesArrayHash.value[1].timeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing
        ephys_data = sess_data.timeSeriesArrayHash.value[1].valueMatrix[1, :] * time_conversion_factor
        time_stamps = sess_data.timeSeriesArrayHash.value[1].time * time_conversion_factor

        # Account for 10ms whisker trial time offset in SAH recordings and different time format between SAH & JY recordings.
        if sess_data_file.as_posix().find('JY'):
            ephys_data = np.hstack([ephys_data[5:], [0, 0, 0, 0, 0]])
        elif sess_data_file.as_posix().find('AH'):
            ephys_data = np.hstack([ephys_data[4:], [0, 0, 0, 0]])
            time_stamps = time_stamps - 0.01

        key['spike_train'] = (ephys_data
                              if not isinstance(ephys_data, sparse.csc_matrix)
                              else np.asarray(ephys_data.todense()).flatten())
        key['spike_timestamps'] = time_stamps

        self.insert1(key)
        print(f'Inserted spike-train data for session: {key["session_id"]}')


@schema
class TrialSegmentedMembranePotential(dj.Computed):
    definition = """
    -> MembranePotential
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_mp=null: longblob   
    segmented_mp_timestamps=null: longblob  # (s)
    """

    key_source = MembranePotential * acquisition.TrialSet * analysis.TrialSegmentationSetting

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        mp, timestamps = (MembranePotential & key).fetch1('membrane_potential', 'membrane_potential_timestamps')

        # Limit to insert size of 15 per insert
        trial_lists = utilities.split_list((acquisition.TrialSet.Trial & key).fetch('KEY'), utilities.insert_size)

        for b_idx, trials in enumerate(trial_lists):
            segmented_mp = [dict(trial_key, **dict(zip(
                ('segmented_mp', 'segmented_mp_timestamps'),
                analysis.perform_trial_segmentation(trial_key, event_name, pre_stim_dur, post_stim_dur, mp, timestamps)
                if not isinstance(analysis.get_event_time(event_name, trial_key, return_exception=True), Exception)
                else (None, None)))) for trial_key in trials]
            self.insert({**key, **s} for s in segmented_mp if s['segmented_mp'] is not None)
            print(f'Segmenting Membrane Potential: {b_idx * utilities.insert_size + len(trials)}/' +
                  f'{(acquisition.TrialSet & key).fetch1("trial_counts")}')


@schema
class TrialSegmentedSpikeTrain(dj.Computed):
    definition = """
    -> SpikeTrain
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_spike_train=null: longblob
    segmented_spike_timestamps: longblob  # (s)
    """

    key_source = SpikeTrain * acquisition.TrialSet * analysis.TrialSegmentationSetting

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        spk, timestamps = (SpikeTrain & key).fetch1('spike_train', 'spike_timestamps')
        # Limit insert batch size
        insert_size = utilities.insert_size
        trial_lists = utilities.split_list((acquisition.TrialSet.Trial & key).fetch('KEY'), insert_size)

        for b_idx, trials in enumerate(trial_lists):
            segmented_spk = [dict(trial_key, **dict(zip(
                ('segmented_spike_train', 'segmented_spike_timestamps'),
                analysis.perform_trial_segmentation(trial_key, event_name, pre_stim_dur, post_stim_dur, spk, timestamps)
                if not isinstance(analysis.get_event_time(event_name, trial_key, return_exception=True), Exception)
                else (None, None)))) for trial_key in trials]

            self.insert({**key, **s} for s in segmented_spk if s['segmented_spike_train'] is not None)
            print(f'Segmenting SpikeTrain: {b_idx * utilities.insert_size + len(trials)}/' +
                  f'{(acquisition.TrialSet & key).fetch1("trial_counts")}')
