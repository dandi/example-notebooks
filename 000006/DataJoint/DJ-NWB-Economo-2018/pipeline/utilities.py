import os
from datetime import datetime
import re

import glob
import numpy as np

from . import reference, acquisition


time_unit_conversion_factor = {'millisecond': 1e-3,
                               'second': 1,
                               'minute': 60,
                               'hour': 3600,
                               'day': 86400}

datetime_formats = ('%Y-%m-%d',)


def parse_date(text):
    for fmt in datetime_formats:
        cover = len(datetime.now().strftime(fmt))
        try:
            return datetime.strptime(text[:cover], fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


def split_list(arr, size):
    slice_from = 0
    while len(arr) > slice_from:
        slice_to = slice_from + size
        yield arr[slice_from:slice_to]
        slice_from = slice_to
        