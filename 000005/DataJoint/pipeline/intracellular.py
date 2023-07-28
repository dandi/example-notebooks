'''
Schema of intracellular information.
'''
import re
import os
import sys
from datetime import datetime

import numpy as np
import scipy.io as sio
from scipy import sparse
import datajoint as dj

from . import reference, utilities, acquisition, analysis

schema = dj.schema(dj.config['custom']['database.prefix'] + 'intracellular')


@schema
class CellType(dj.Lookup):
    definition = """
    cell_type: varchar(12)
    """
    contents = zip(['excitatory', 'inhibitory', 'FSIN', 'fast-spiking', 'N/A'])


@schema
class Cell(dj.Manual):
    definition = """ # A cell undergone intracellular recording in this session
    -> acquisition.Session
    ---
    -> CellType
    -> reference.ActionLocation
    -> reference.WholeCellDevice
    """


@schema
class MembranePotential(dj.Imported):
    definition = """ # Membrane potential recording from a cell
    -> Cell
    ---
    membrane_potential: longblob  # (mV)
    membrane_potential_timestamps: longblob  # (s)
    """

    def make(self, key):
        return NotImplementedError


@schema
class CurrentInjection(dj.Imported):
    definition = """ # Current injection recording from a cell
    -> Cell
    ---
    current_injection: longblob  # (mV)
    current_injection_timestamps: longblob  # (s)
    """

    def make(self, key):
        return NotImplementedError


@schema
class UnitSpikeTimes(dj.Imported):
    definition = """ # Spike times of this Cell
    -> Cell
    unit_id: smallint
    ---
    spike_times: longblob  # (s)
    """

    def make(self, key):
        return NotImplementedError


@schema
class TrialSegmentedMembranePotential(dj.Computed):
    definition = """
    -> MembranePotential
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_mp=null: longblob   
    """

    key_source = MembranePotential * acquisition.TrialSet * analysis.TrialSegmentationSetting

    def make(self, key):
        return NotImplementedError


@schema
class TrialSegmentedUnitSpikeTimes(dj.Computed):
    definition = """
    -> UnitSpikeTimes
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_spike_times=null: longblob
    """

    def make(self, key):
        return NotImplementedError
