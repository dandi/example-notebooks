
'''
MAP Motion Tracking Schema
'''

import datajoint as dj

from . import experiment
from . import get_schema_name

schema = dj.schema(get_schema_name('tracking'))
[experiment]  # NOQA flake8



@schema
class LickTrace(dj.Imported):
    definition = """
    -> experiment.SessionTrial
    ---
    lick_trace: longblob
    lick_trace_timestamps: longblob
    """