import sys

import numpy as np
import datajoint as dj
import tqdm

from . import (acquisition, analysis)

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'extracellular')


@schema
class ProbeInsertion(dj.Manual):
    definition = """ # Description of probe insertion details during extracellular recording
    -> acquisition.Session
    -> reference.Probe
    -> reference.BrainLocation
    insertion_depth: decimal(6,2)  #  (um)
    """


@schema
class UnitSpikeTimes(dj.Manual):
    definition = """ 
    -> ProbeInsertion
    unit_id : smallint
    ---
    -> reference.Probe.Channel
    unit_cell_type: enum('PTlower', 'PTupper', 'unidentified', 'L6 corticothalamic')  #  depending on the animal (which cell-type being tagged)
    unit_quality="": varchar(32)  #  quality of the spike sorted unit (e.g. excellent, good, poor, fair, etc.)
    unit_depth: float  # (um)
    spike_times: longblob  # (s) time of each spike, with respect to the start of session 
    """


@schema
class TrialSegmentedUnitSpikeTimes(dj.Computed):
    definition = """
    -> UnitSpikeTimes
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_spike_times: longblob
    """

    key_source = ProbeInsertion * analysis.TrialSegmentationSetting

    def make(self, key):
        unit_ids, spike_times = (UnitSpikeTimes & key).fetch('unit_id', 'spike_times')  # spike_times from all units
        trial_keys = (acquisition.TrialSet.Trial & key).fetch('KEY')

        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')

        for trial_key in tqdm.tqdm(trial_keys):
            # get event time - this is done per trial
            try:
                event_time_point = analysis.get_event_time(event_name, trial_key)
            except analysis.EventChoiceError as e:
                print(f'Trial segmentation error - Msg: {str(e)}', file = sys.stderr)
                continue

            event_time_point = event_time_point + (acquisition.TrialSet.Trial & trial_key).fetch1('start_time')
            pre_stim_dur = float(pre_stim_dur)
            post_stim_dur = float(post_stim_dur)

            seg_trial_spike_times = [spk[np.logical_and((spk >= (event_time_point - pre_stim_dur)),
                                                        (spk <= (event_time_point + post_stim_dur)))] - event_time_point
                                     for spk in spike_times]

            self.insert(dict({**key, **trial_key},
                             unit_id = u_id,
                             segmented_spike_times = spk)
                        for u_id, spk in zip(unit_ids, seg_trial_spike_times))


@schema
class PSTH(dj.Computed):
    definition = """  # PSTH per unit, per trial, time-locked to the response period (cue-start event)
    -> TrialSegmentedUnitSpikeTimes
    ---
    psth: longblob
    psth_time: longblob    
    """

    def make(self, key):
        return NotImplementedError



