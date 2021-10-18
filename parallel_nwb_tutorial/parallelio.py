import numpy as np
from dateutil import tz
from datetime import datetime

from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from mpi4py import MPI
from hdmf.data_utils import DataChunkIterator

start_time = datetime(2018, 4, 25, 2, 30, 3, tzinfo=tz.gettz('US/Pacific'))
fname = 'test_parallel_pynwb.nwb'
rank = MPI.COMM_WORLD.rank  # The process ID (integer 0-3 for 4-process run)

# Create file on one rank. Here we only instantiate the dataset we want to
# write in parallel but we do not write any data
if rank == 0:
    nwbfile = NWBFile('aa', 'aa', start_time)
    data = DataChunkIterator(data=None, maxshape=(MPI.COMM_WORLD.size,), dtype=np.dtype('int'))

    nwbfile.add_acquisition(TimeSeries('ts_name', description='desc', data=data,
                                       rate=100., unit='m'))
    with NWBHDF5IO(fname, 'w') as io:
        io.write(nwbfile)

# write to dataset in parallel
with NWBHDF5IO(fname, 'a', comm=MPI.COMM_WORLD) as io:
    nwbfile = io.read()
    print(rank)
    nwbfile.acquisition['ts_name'].data[rank] = rank

# read from dataset in parallel
with NWBHDF5IO(fname, 'r', comm=MPI.COMM_WORLD) as io:
    print(io.read().acquisition['ts_name'].data[rank])
