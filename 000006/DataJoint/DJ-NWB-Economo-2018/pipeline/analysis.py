# -*- coding: utf-8 -*-
'''
Schema of analysis data.
'''

import numpy as np
import datajoint as dj

from . import acquisition

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'analysis')


@schema
class TrialSegmentationSetting(dj.Lookup):
    definition = """ 
    trial_seg_setting: smallint
    ---
    -> reference.ExperimentalEvent
    pre_stim_duration: decimal(6,4)  # (s) pre-stimulus duration
    post_stim_duration: decimal(6,4)  # (s) post-stimulus duration
    """
    contents = [[0, 'cue_start', 3.3975, 2.9975]]


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



def get_event_time(event_name, key):
    # get event time
    try:
        t = (acquisition.TrialSet.EventTime & key & {'trial_event': event_name}).fetch1('event_time')
    except dj.DataJointError:
        raise EventChoiceError(event_name, f'{event_name}: event not found')
    if np.isnan(t):
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
