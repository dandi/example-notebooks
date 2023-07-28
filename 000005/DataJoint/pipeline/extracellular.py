'''
Schema of extracellular information.
'''
import re
import os
import sys
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj
import tqdm

from . import reference, utilities, acquisition, analysis

schema = dj.schema(dj.config['custom']['database.prefix'] + 'extracellular')


@schema
class ProbeInsertion(dj.Manual):
    definition = """ # Description of probe insertion details during extracellular recording
    -> acquisition.Session
    -> reference.Probe
    """

    class InsertLocation(dj.Part):
        definition = """
        -> master
        -> reference.Probe.Shank
        -> reference.ActionLocation
        """


@schema
class Voltage(dj.Imported):
    definition = """
    -> ProbeInsertion
    ---
    voltage: longblob   # (mV)
    voltage_start_time: float # (second) first timepoint of voltage recording
    voltage_sampling_rate: float # (Hz) sampling rate of voltage recording
    """

    def make(self, key):
        # this function implements the ingestion of raw extracellular data into the pipeline
        return NotImplementedError


@schema
class UnitSpikeTimes(dj.Manual):
    definition = """ 
    -> ProbeInsertion
    unit_id : smallint
    ---
    spike_times: longblob  # (s) time of each spike, with respect to the start of session 
    cell_desc='N/A': varchar(32)  # e.g. description of this unit (e.g. cell type)  
    """

    class UnitChannel(dj.Part):
        definition = """
        -> master
        -> reference.Probe.Channel
        """

    class SpikeWaveform(dj.Part):
        definition = """
        -> master
        -> UnitSpikeTimes.UnitChannel
        ---
        spike_waveform: longblob  # waveform(s) of each spike at each spike time (waveform_timestamps x spike_times)
        """


@schema
class TrialSegmentedUnitSpikeTimes(dj.Imported):
    definition = """
    -> UnitSpikeTimes
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_spike_times: longblob  # (s) with respect to the start of the trial
    """

    def make(self, key):
        return NotImplementedError
