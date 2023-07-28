# -*- coding: utf-8 -*-
'''
Schema of analysis data.
'''
import re
import os
import sys
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj

from . import reference, utilities, acquisition

schema = dj.schema(dj.config['custom']['database.prefix'] + 'analysis')


@schema
class TrialSegmentationSetting(dj.Lookup):
    definition = """ 
    trial_seg_setting: smallint
    ---
    -> reference.ExperimentalEvent
    pre_stim_duration: decimal(4,2)  # (s) pre-stimulus duration
    post_stim_duration: decimal(4,2)  # (s) post-stimulus duration
    """
    contents = [[0, 'trial_start', 0, 4],
                [1, 'first_touch', 1, 4]]


@schema
class RealignedEvent(dj.Computed):
    definition = """
    -> TrialSegmentationSetting
    -> acquisition.TrialSet.Trial
    """

    class RealignedEventTime(dj.Part):
        definition = """ # experimental paradigm event timing marker(s) for this trial
        -> master
        -> acquisition.TrialSet.EventTime
        ---
        realigned_event_time = null: float   # (s) event time with respect to the event this trial-segmentation is time-locked to
        """

    def make(self, key):
        self.insert1(key)
        # get event, pre/post stim duration
        event_of_interest, pre_stim_dur, post_stim_dur = (TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get event time
        try:
            eoi_time_point = get_event_time(event_of_interest, key)
        except EventChoiceError as e:
            print(f'Event Choice error - Msg: {str(e)}')
            return
        # get all other events for this trial
        events, event_times = (acquisition.TrialSet.EventTime & key).fetch('trial_event', 'event_time')
        self.RealignedEventTime.insert(dict(key,
                                            trial_event = eve,
                                            realigned_event_time = event_times[e_idx] - eoi_time_point)
                                       for e_idx, eve in enumerate(events))


def perform_trial_segmentation(trial_key, event_name, pre_stim_dur, post_stim_dur, data, timestamps):
        # get event time
        try:
            event_time_point = get_event_time(event_name, trial_key)
        except EventChoiceError as e:
            raise e
        #
        pre_stim_dur = float(pre_stim_dur)
        post_stim_dur = float(post_stim_dur)
        fs = 1/np.median(np.diff(timestamps))
        # check if pre/post stim dur is within start/stop time, if not, pad with NaNs
        trial_start, trial_stop = (acquisition.TrialSet.Trial & trial_key).fetch1('start_time', 'stop_time')
        event_time_point = event_time_point + trial_start

        pre_stim_nan_count = 0
        post_stim_nan_count = 0
        if event_time_point - pre_stim_dur < trial_start:
            pre_stim_nan_count = int((trial_start - (event_time_point - pre_stim_dur)) * fs)
            pre_stim_dur = event_time_point - trial_start
        if event_time_point + post_stim_dur > trial_stop:
            post_stim_nan_count = int((event_time_point + post_stim_dur - trial_stop) * fs)
            post_stim_dur = trial_stop - event_time_point

        segmented_data = data[np.logical_and((timestamps >= (event_time_point - pre_stim_dur)),
                                             (timestamps <= (event_time_point + post_stim_dur)))]
        # pad with NaNs
        segmented_data = np.hstack((np.full(pre_stim_nan_count, np.nan), segmented_data,
                                    np.full(post_stim_nan_count, np.nan)))

        return segmented_data


def get_event_time(event_name, key, return_exception=False):
    # get event time
    try:
        t = (acquisition.TrialSet.EventTime & key & {'trial_event': event_name}).fetch1('event_time')
    except dj.DataJointError:
        if return_exception:
            return EventChoiceError(event_name, f'{event_name}: event not found')
        else:
            raise EventChoiceError(event_name, f'{event_name}: event not found')
    if np.isnan(t):
        if return_exception:
            return EventChoiceError(event_name, msg = f'{event_name}: event_time is nan')
        else:
            raise EventChoiceError(event_name, msg = f'{event_name}: event_time is nan')
    else:
        return t


class EventChoiceError(Exception):
    '''Raise when "event" does not exist or "event_type" is invalid (e.g. nan)'''
    def __init__(self, event_name, msg=None):
        if msg is None:
            msg = f'Invalid event type or time for: {event_name}'
        super().__init__(msg)
        self.event_name = event_name
    pass
