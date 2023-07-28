'''
Schema of behavioral information.
'''
import re
import os
from datetime import datetime
import pathlib
import numpy as np
import scipy.io as sio
import datajoint as dj
import h5py as h5

from . import reference, subject, utilities, stimulation, acquisition, analysis


schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'behavior')

sess_data_dir = pathlib.Path(dj.config['custom'].get('intracellular_directory')).as_posix()


@schema
class LickTrace(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    lick_trace_left: longblob   
    lick_trace_right: longblob
    lick_trace_start_time: float # (s) first timepoint of lick trace recording
    lick_trace_sampling_rate: float # (Hz) sampling rate of lick trace recording
    """

    def make(self, key):
        # ============ Dataset ============
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
        # Search the files in filenames to find a match for "this" session (based on key)
        sess_data_file = utilities.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
        if sess_data_file is None:
            raise FileNotFoundError(f'BehaviorAcquisition import failed for: {animal_id} - {date_of_experiment}')
        nwb = h5.File(os.path.join(sess_data_dir, sess_data_file), 'r')
        #  ============= Now read the data and start ingesting =============
        print('Insert behavioral data for: subject: {0} - date: {1}'.format(key['subject_id'], key['session_time']))
        key['lick_trace_left'] = nwb['acquisition']['timeseries']['lick_trace_L']['data'].value
        key['lick_trace_right'] = nwb['acquisition']['timeseries']['lick_trace_R']['data'].value
        lick_trace_time_stamps = nwb['acquisition']['timeseries']['lick_trace_R']['timestamps'].value
        key['lick_trace_start_time'] = lick_trace_time_stamps[0]
        key['lick_trace_sampling_rate'] = 1 / np.mean(np.diff(lick_trace_time_stamps))
        self.insert1(key)


@schema
class TrialSegmentedLickTrace(dj.Computed):
    definition = """
    -> LickTrace
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_lt_left: longblob   
    segmented_lt_right: longblob
    """

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        fs, first_time_point, lt_left, lt_right = (LickTrace & key).fetch1(
            'lick_trace_sampling_rate', 'lick_trace_start_time', 'lick_trace_left', 'lick_trace_right')
        # segmentation
        key['segmented_lt_left'] = analysis.perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur,
                                                              lt_left, fs, first_time_point)
        key['segmented_lt_right'] = analysis.perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur,
                                                               lt_right, fs, first_time_point)
        self.LickTrace.insert1(key)
        print(f'Perform trial-segmentation of lick traces for trial: {key["trial_id"]}')
