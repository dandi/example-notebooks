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
import h5py as h5

from . import utilities, acquisition, analysis


schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'behavior')


@schema
class LickTimes(dj.Manual):
    definition = """
    -> acquisition.Session
    ---
    lick_left_times: longblob  # (s), lick left onset times (based on contact of lick port)
    lick_right_times: longblob  # (s), lick right onset times (based on contact of lick port)
    """
