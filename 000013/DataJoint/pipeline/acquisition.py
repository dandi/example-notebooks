'''
Schema of aquisition information.
'''
import re
import os
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj
from tqdm import tqdm

from . import reference, subject, utilities

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'acquisition')


@schema
class ExperimentType(dj.Lookup):
    definition = """
    experiment_type: varchar(64)
    """
    contents = [['behavior'], ['extracelluar'], ['photostim']]


@schema
class Session(dj.Manual):
    definition = """
    -> subject.Subject
    session_time: datetime    # session time
    session_id: varchar(24)
    ---
    session_directory = "": varchar(256)
    session_note = "": varchar(256) 
    """

    class Experimenter(dj.Part):
        definition = """
        -> master
        -> reference.Experimenter
        """

    class ExperimentType(dj.Part):
        definition = """
        -> master
        -> ExperimentType
        """


@schema
class TrialSet(dj.Imported):
    definition = """
    -> Session
    ---
    trial_counts: int # total number of trials
    """
    
    class Trial(dj.Part):
        definition = """
        -> master
        trial_id: smallint           # id of this trial in this trial set
        ---
        start_time = null: float               # start time of this trial, with respect to starting point of this session
        stop_time = null: float                # end time of this trial, with respect to starting point of this session
        -> reference.TrialType
        -> reference.TrialResponse
        trial_stim_present: bool  # is this a stim or no-stim trial
        pole_position: float  # (mm)  the location of the pole along the anteroposterior axis of the animal
        """
        
    class EventTime(dj.Part):
        definition = """ # experimental paradigm event timing marker(s) for this trial
        -> master.Trial
        -> reference.ExperimentalEvent.proj(trial_event="event")
        ---
        event_time=null: float   # (in second) event time with respect to this trial's start time
        """

    def make(self, key):
        sess_data_file = utilities.find_session_matched_matfile(key)
        if sess_data_file is None:
            print(f'Trial import failed for session: {key["session_id"]}')
            return
        sess_data = sio.loadmat(sess_data_file, struct_as_record = False, squeeze_me = True)['c']
        key['trial_counts'] = len(sess_data.trialIds)
        self.insert1(key)

        # read trial info
        ephys_time_conversion_factor = utilities.time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.timeSeriesArrayHash.value[1].timeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing
        trial_time_conversion_factor = utilities.time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.trialTimeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing
        behav_time_conversion_factor = utilities.time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.timeSeriesArrayHash.value[0].timeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing
        pole_in_times = sess_data.trialPropertiesHash.value[1] * trial_time_conversion_factor
        pole_out_times = sess_data.trialPropertiesHash.value[2] * trial_time_conversion_factor
        lick_times = sess_data.trialPropertiesHash.value[3] * trial_time_conversion_factor
        time_stamps = sess_data.timeSeriesArrayHash.value[1].time * ephys_time_conversion_factor
        touchon = sess_data.timeSeriesArrayHash.value[0].valueMatrix[6, :]
        behav_time_stamps = sess_data.timeSeriesArrayHash.value[0].time * behav_time_conversion_factor

        # Handling some major inconsistency in the data set: some .mat files have behavior-trial
        # (sess_data.timeSeriesArrayHash.value[0].trial) matches with trialIds (sess_data.trialIds),
        # however some .mat files have sess_data.timeSeriesArrayHash.value[0].trial = 1, 2, 3 ... len(sess_data.trialIds)
        if set(sess_data.timeSeriesArrayHash.value[0].trial) == set(sess_data.trialIds):
            trial_idx = sess_data.timeSeriesArrayHash.value[0].trial
        else:
            trial_idx = np.array([sess_data.trialIds[tr] for tr in (sess_data.timeSeriesArrayHash.value[0].trial - 1)])

        for idx, trial_id in tqdm(enumerate(sess_data.trialIds)):
            key['trial_id'] = int(trial_id)
            key['start_time'] = time_stamps[np.where(
                sess_data.timeSeriesArrayHash.value[1].trial == int(trial_id))[0][0]]
            key['stop_time'] = min(time_stamps[np.where(
                sess_data.timeSeriesArrayHash.value[1].trial == int(trial_id))[0][-1]], time_stamps[-1])
            key['trial_response'] = sess_data.trialTypeStr[np.where(sess_data.trialTypeMat[:-1, idx] == 1)[0][0]]
            key['trial_stim_present'] = int(sess_data.trialTypeMat[-1, idx] == 1)  # why DJ throws int type error for bool??
            key['trial_type'] = sess_data.trialPropertiesHash.value[-1][idx]
            key['pole_position'] = sess_data.trialPropertiesHash.value[0][idx] * 0.0992  # convert to micron here (0.0992 microns / microstep)
            self.Trial.insert1(key, ignore_extra_fields=True)
            # ======== Now add trial event timing to the EventTime part table ====
            event_dict = dict(trial_start=0,
                              trial_stop=key['stop_time'] - key['start_time'],
                              pole_in=pole_in_times[idx],
                              pole_out=pole_out_times[idx],
                              first_lick=lick_times[idx][0] if len(lick_times[idx]) > 0 else np.nan)
            self.EventTime.insert((dict(key, trial_event=k, event_time=v)
                                       for k, v in event_dict.items()),
                                      ignore_extra_fields=True)
