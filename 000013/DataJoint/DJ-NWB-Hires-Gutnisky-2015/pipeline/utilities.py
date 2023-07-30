import os
from datetime import datetime
import re
import datajoint as dj
import pathlib

insert_size = 10

time_unit_conversion_factor = {'millisecond': 1e-3,
                               'second': 1,
                               'minute': 60,
                               'hour': 3600,
                               'day': 86400}

datetime_formats = ('%y%m%d', '%y%d%m')
data_dir = pathlib.Path(dj.config['custom'].get('data_directory'))


def parse_date(text):
    for fmt in datetime_formats:
        cover = len(datetime.now().strftime(fmt))
        try:
            return datetime.strptime(text[:cover], fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


def find_session_matched_matfile(sess_key):
    """
    Search the filenames to find a match for "this" session (based on key)
    """
    sess_data_dir = data_dir / 'datafiles'
    matched_sess_data_file = sess_data_dir.glob(f'*{sess_key["session_id"]}*.mat')
    try:
        return next(matched_sess_data_file)
    except:
        return None


def split_list(arr, chunk_size):
    for s in range(0, len(arr), chunk_size):
        yield arr[s:s+chunk_size]
