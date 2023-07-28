import logging

import datajoint as dj
from datetime import datetime
import hashlib
import numpy as np
from scipy import signal

log = logging.getLogger(__name__)

if 'custom' not in dj.config:
    dj.config['custom'] = {}

datetime_formats = ('%Y%m%d %H%M%S', '%Y%m%d')

time_unit_conversion_factor = {'millisecond': 1e-3,
                               'second': 1,
                               'minute': 60,
                               'hour': 3600,
                               'day': 86400}

def parse_date(text):
    for fmt in datetime_formats:
        cover = len(datetime.now().strftime(fmt))
        try:
            return datetime.strptime(text[:cover], fmt)
        except ValueError:
            pass
    raise ValueError(f'no valid date format found - {text}')


default_prefix = dj.config['custom'].get('database.prefix', 'li2015_v1_')
def get_schema_name(name):
    try:
        return dj.config['custom']['{}.database'.format(name)]
    except KeyError:
        if name.startswith('ingest'):
            prefix = '{}_ingest_'.format(dj.config.get('database.user', default_prefix))
        else:
            prefix = default_prefix
    return prefix + name


class InsertBuffer(object):
    '''
    InsertBuffer: a utility class to help managed chunked inserts

    Currently requires records do not have prerequisites.
    '''
    def __init__(self, rel, chunksz=1, **insert_args):
        self._rel = rel
        self._queue = []
        self._chunksz = chunksz
        self._insert_args = insert_args

    def insert1(self, r):
        self._queue.append(r)

    def insert(self, recs):
        self._queue += recs

    def flush(self, chunksz=None):
        '''
        flush the buffer
        XXX: also get pymysql.err.DataError, etc - catch these or pr datajoint?
        XXX: optional flush-on-error? hmm..
        '''
        qlen = len(self._queue)
        if chunksz is None:
            chunksz = self._chunksz

        if qlen > 0 and qlen % chunksz == 0:
            try:
                self._rel.insert(self._queue, **self._insert_args)
                self._queue.clear()
                return qlen
            except dj.DataJointError as e:
                raise

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etraceback):
        if etype:
            raise evalue
        else:
            return self.flush(1)


def dict_to_hash(key):
    """
	Given a dictionary `key`, returns a hash string
    """
    hashed = hashlib.md5()
    for k, v in sorted(key.items()):
        hashed.update(str(v).encode())
    return hashed.hexdigest()


def smooth_psth(data, window_size=None):

    window_size = int(.03 * len(data)) if not window_size else int(window_size)
    kernel = np.full((window_size, ), 1/window_size)

    return signal.convolve(data, kernel, mode='same')
