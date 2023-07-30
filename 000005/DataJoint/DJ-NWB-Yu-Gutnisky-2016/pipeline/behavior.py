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

from . import utilities, reference, acquisition, analysis, intracellular


schema = dj.schema(dj.config['custom']['database.prefix'] + 'behavior')


@schema
class Whisker(dj.Imported):
    definition = """ # Whisker Behavior data
    -> acquisition.Session
    -> reference.WhiskerConfig
    ---
    principal_whisker=0: bool           #  is this the principal whisker
    pole_available=null: longblob       #  binary array of time when the pole is within reach of the whisker
    touch_offset=null: longblob         #  binary array of all touch offset times (1 = offset) 
    touch_onset=null: longblob          #  binary array of all touch onset times (1 = onset)
    whisker_angle=null: longblob        #  (degree) the angle of the whisker relative to medialateral axis of the animal
    whisker_curvature=null: longblob    #  the change in whisker curvature
    behavior_timestamps=null: longblob  #  (s)
    """

    def make(self, key):
        raise NotImplementedError


@schema
class LickTrace(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    lick_trace: longblob   
    lick_trace_timestamps: longblob # (s) 
    """

