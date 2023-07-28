'''
Schema of behavioral information.
'''
import re
import os
from datetime import datetime
import sys

import numpy as np
import scipy.io as sio
import datajoint as dj
from collections import ChainMap

from . import utilities, acquisition, analysis, intracellular


schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'behavior')


@schema
class Behavior(dj.Imported):
    definition = """ # Behavior data
    -> acquisition.Session
    ---
    theta_at_base=null: longblob        #  (degree) the angle of the whisker base relative to medialateral axis of the animal
    amplitude=null: longblob            #  the amplitude of the Hilbert Transform of theta_at_base
    phase=null: longblob                #  the phase of the Hilbert Transform of theta_at_base
    set_point=null: longblob            #  the amplitude of the Hilbert Transform of theta_at_base
    theta_filt=null: longblob           #  theta_at_base filtered with 6-60Hz bandpass
    delta_kappa=null: longblob          #  the change in whisker curvature following each touch onset 
    touch_onset=null: longblob          #  binary array of all touch onset times (1 = onset)
    touch_offset=null: longblob         #  binary array of all touch offset times (1 = offset) 
    distance_to_pole=null: longblob     #  (mm) the shortest distance from whisker to the pole 
    pole_available=null: longblob       #  binary array of time when the pole is within reach of the whisker
    beam_break_times=null: longblob     #  binary array of lick times (1 = onset of spout contact)
    behavior_timestamps=null: longblob  #  (s)
    """

    def make(self, key):
        sess_data_file = utilities.find_session_matched_matfile(key)
        if sess_data_file is None:
            raise FileNotFoundError(f'Behavioral data import failed for session: {key["session_id"]}')
        sess_data = sio.loadmat(sess_data_file, struct_as_record = False, squeeze_me = True)['c']
        # time_conversion_factor = utilities.time_unit_conversion_factor[
        #     sess_data.timeUnitNames[sess_data.timeSeriesArrayHash.value[0].timeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing

        time_conversion_factor = utilities.time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.timeSeriesArrayHash.value[1].timeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing
        time_stamps = sess_data.timeSeriesArrayHash.value[1].time * time_conversion_factor

        key['behavior_timestamps'] = time_stamps[::10]

        behavior_data = sess_data.timeSeriesArrayHash.value[0].valueMatrix

        behavioral_keys = ['theta_at_base', 'amplitude', 'phase', 'set_point', 'theta_filt',
                           'delta_kappa', 'touch_onset', 'touch_offset', 'distance_to_pole',
                           'pole_available', 'beam_break_times']
        self.insert1({**key, **{k: v
                                for k, v in zip(behavioral_keys, behavior_data)}})
        print(f'Inserted behavioral data for session: {key["session_id"]}')


@schema
class TrialSegmentedBehavior(dj.Computed):
    definition = """
    -> Behavior
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_theta_at_base=null: longblob  #
    segmented_amplitude=null: longblob  #
    segmented_phase=null: longblob  #
    segmented_set_point=null: longblob  #
    segmented_theta_filt=null: longblob  #
    segmented_delta_kappa=null: longblob  #
    segmented_touch_onset=null: longblob  #
    segmented_touch_offset=null: longblob  #
    segmented_distance_to_pole=null: longblob  #
    segmented_pole_available=null: longblob  #
    segmented_beam_break_times=null: longblob  #
    segmented_behavior_timestamps=null: longblob  # (s)
    """

    key_source = Behavior * acquisition.TrialSet * analysis.TrialSegmentationSetting

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        behavior = (Behavior & key).fetch1()
        [behavior.pop(k) for k in Behavior.primary_key]
        timestamps = behavior.pop('behavior_timestamps')
        # Limit insert batch size
        insert_size = utilities.insert_size
        trial_lists = utilities.split_list((acquisition.TrialSet.Trial & key).fetch('KEY'), insert_size)

        for b_idx, trials in enumerate(trial_lists):
            segmented_behav = [{**trial_key, **(ChainMap(*[dict(zip(
                (f'segmented_{k}', 'segmented_behavior_timestamps'),
                analysis.perform_trial_segmentation(trial_key, event_name, pre_stim_dur, post_stim_dur, v, timestamps)))
                                                    for k, v in behavior.items()])
                                                if not isinstance(analysis.get_event_time(event_name, trial_key,
                                                                                          return_exception=True), Exception)
                                                else dict())}
                               for trial_key in trials]
            self.insert({**key, **s} for s in segmented_behav if 'segmented_amplitude' in s)
            print(f'Segmenting behavioral data: {b_idx * utilities.insert_size + len(trials)}/' +
                  f'{(acquisition.TrialSet & key).fetch1("trial_counts")}')
