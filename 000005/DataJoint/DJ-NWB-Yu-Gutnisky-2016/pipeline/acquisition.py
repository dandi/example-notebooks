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

schema = dj.schema(dj.config['custom']['database.prefix'] + 'acquisition')


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
    session_id: varchar(32)
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
        pole_position=null: float  # (mm) the location of the pole along the anteroposterior axis of the animal
        """
        
    class EventTime(dj.Part):
        definition = """ # experimental paradigm event timing marker(s) for this trial
        -> master.Trial
        -> reference.ExperimentalEvent.proj(trial_event="event")
        ---
        event_time=null: float   # (in second) event time with respect to this trial's start time
        """

    def make(self, key):
        return NotImplementedError

