
import datajoint as dj

from . import lab, experiment
from . import get_schema_name

import numpy as np

schema = dj.schema(get_schema_name('ephys'))
[lab, experiment]  # NOQA flake8


@schema
class ProbeInsertion(dj.Manual):
    definition = """
    -> experiment.Session
    insertion_number: int
    ---
    -> lab.ElectrodeConfig
    """

    class InsertionLocation(dj.Part):
        definition = """
        -> master
        ---
        -> lab.SkullReference
        ap_location: decimal(6, 2) # (um) from ref; anterior is positive; based on manipulator coordinates/reconstructed track
        ml_location: decimal(6, 2) # (um) from ref ; right is positive; based on manipulator coordinates/reconstructed track
        dv_location: decimal(6, 2) # (um) from dura to first site of the probe; ventral is negative; based on manipulator coordinates/reconstructed track
        theta=null:  decimal(5, 2) # (deg) - elevation - rotation about the ml-axis [0, 180] - w.r.t the z+ axis
        phi=null:    decimal(5, 2) # (deg) - azimuth - rotation about the dv-axis [0, 360] - w.r.t the x+ axis
        beta=null:   decimal(5, 2) # (deg) rotation about the shank of the probe
        """

    class RecordableBrainRegion(dj.Part):
        definition = """
        -> master
        -> lab.BrainArea
        -> lab.Hemisphere
        """

    class InsertionNote(dj.Part):
        definition = """
        -> master
        ---
        insertion_note: varchar(1000)
        """

    class ElectrodeSitePosition(dj.Part):
        definition = """
        -> master
        -> lab.ElectrodeConfig.Electrode
        ---
        electrode_posx: float
        electrode_posy: float
        electrode_posz: float
        """


@schema
class LFP(dj.Imported):
    definition = """
    -> ProbeInsertion
    ---
    lfp_sample_rate: float          # (Hz)
    lfp_time_stamps: longblob       # timestamps with respect to the start of the recording (recording_timestamp)
    lfp_mean: longblob              # mean of LFP across electrodes
    """

    class Channel(dj.Part):
        definition = """  
        -> master
        -> lab.ElectrodeConfig.Electrode
        ---
        lfp: longblob           # recorded lfp at this electrode
        """


@schema
class UnitQualityType(dj.Lookup):
    definition = """
    # Quality
    unit_quality  :  varchar(100)
    ---
    unit_quality_description :  varchar(4000)
    """
    contents = [
        ('good', 'single unit'),
        ('ok', 'probably a single unit, but could be contaminated'),
        ('multi', 'multi unit'),
        ('all', 'all units')
    ]


@schema
class CellType(dj.Lookup):
    definition = """
    #
    cell_type  :  varchar(100)
    ---
    cell_type_description :  varchar(4000)
    """
    contents = [
        ('Pyr', 'putative pyramidal neuron'),
        ('interneuron', 'interneuron'),
        ('PT', 'pyramidal tract neuron'),
        ('IT', 'intratelecephalic neuron'),
        ('FS', 'fast spiking'),
        ('N/A', 'unknown')
    ]


@schema
class ClusteringMethod(dj.Lookup):
    definition = """
    clustering_method: varchar(16)
    """

    contents = zip(['jrclust', 'kilosort', 'manual'])


@schema
class Unit(dj.Imported):
    """
    A certain portion of the recording is used for clustering (could very well be the entire recording)
    Thus, spike-times are relative to the 1st time point in this portion
    E.g. if clustering is performed from trial 8 to trial 200, then spike-times are relative to the start of trial 8
    """
    definition = """
    # Sorted unit
    -> ProbeInsertion
    -> ClusteringMethod
    unit: smallint
    ---
    unit_uid=null: int # unique across sessions/animals
    -> UnitQualityType
    -> lab.ElectrodeConfig.Electrode # site on the electrode for which the unit has the largest amplitude
    unit_posx : double # (um) estimated x position of the unit relative to probe's (0,0)
    unit_posy : double # (um) estimated y position of the unit relative to probe's (0,0)
    spike_times : longblob  # (s) from the start of the first data point used in clustering
    unit_amp=null: double
    unit_snr=null: double
    waveform : longblob # spike waveform (#spike x #time)
    """


@schema
class UnitComment(dj.Manual):
    definition = """
    -> Unit
    unit_comment : varchar(767)
    """


@schema
class UnitCellType(dj.Computed):
    definition = """
    -> Unit
    -> CellType
    """


@schema
class TrialSpikes(dj.Computed):
    definition = """
    #
    -> Unit
    -> experiment.SessionTrial
    ---
    spike_times : longblob # (s) spike times for each trial, relative to go cue
    """


@schema
class UnitStat(dj.Computed):
    definition = """
    -> Unit
    ---
    isi_violation=null: float    # 
    avg_firing_rate=null: float  # (Hz)
    """

    isi_violation_thresh = 0.002  # violation threshold of 2 ms

    key_source = ProbeInsertion & experiment.SessionTrial.proj() - (experiment.SessionTrial * Unit - TrialSpikes.proj())

    def make(self, key):
        def make_insert():
            for unit in (Unit & key).fetch('KEY'):
                trial_spikes, tr_start, tr_stop = (TrialSpikes * experiment.SessionTrial & unit).fetch(
                    'spike_times', 'start_time', 'stop_time')
                isi = np.hstack(np.diff(spks) for spks in trial_spikes)
                yield {**unit,
                       'isi_violation': sum((isi < self.isi_violation_thresh).astype(int)) / len(isi) if isi.size else None,
                       'avg_firing_rate': len(np.hstack(trial_spikes)) / sum(tr_stop - tr_start) if isi.size else None}
        self.insert(make_insert())
