import re
import os
import sys
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj
import h5py as h5

from . import reference, subject, utilities

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'acquisition')


@schema
class Session(dj.Manual):
    definition = """
    -> subject.Subject
    session_time: datetime    # session time
    session_id: smallint
    ---
    session_directory = "": varchar(256)
    session_note = "": varchar(256) 
    """

    class Experimenter(dj.Part):
        definition = """
        -> master
        -> reference.Experimenter
        """


@schema
class TrialSet(dj.Manual):
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
        start_time = null: float     # start time of this trial, with respect to the starting point of this session
        -> reference.TrialType
        -> reference.TrialResponse
        trial_stim_present: bool     # is this a stim or no-stim trial
        trial_is_good: bool  # good/bad status of trial (bad trials are not analyzed)
        """

    class EventTime(dj.Part):
        definition = """ # experimental paradigm event timing marker(s) for this trial, relative to trial start time
        -> master.Trial
        -> reference.ExperimentalEvent.proj(trial_event="event")
        ---
        event_time = null: float   # (in second) event time with respect to this trial's start time
        """
