'''
Schema of extracellular information.
'''
import re
import os
from datetime import datetime
import pathlib
import numpy as np
import scipy.io as sio
import datajoint as dj
import h5py as h5
import tqdm

from . import reference, utilities, acquisition, analysis

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'extracellular')

sess_data_dir = pathlib.Path(dj.config['custom'].get('extracellular_directory')).as_posix()


@schema
class ProbeInsertion(dj.Manual):
    definition = """ # Description of probe insertion details during extracellular recording
    -> acquisition.Session
    -> reference.Probe
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
        return None


@schema
class UnitSpikeTimes(dj.Imported):
    definition = """ 
    -> ProbeInsertion
    unit_id : smallint
    ---
    -> reference.Probe.Channel
    spike_times: longblob               # (s) time of each spike, with respect to the start of session 
    unit_cell_type: varchar(32)         # e.g. cell-type of this unit (e.g. wide width, narrow width spiking)
    unit_x: float                       # (mm)
    unit_y: float                       # (mm)
    unit_z: float                       # (mm)
    spike_waveform: longblob            # waveform(s) of each spike at each spike time (spike_time x waveform_timestamps)
    """

    def make(self, key):
        # ================ Dataset ================
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
        # Search the files in filenames to find a match for "this" session (based on key)
        sess_data_file = utilities.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
        if sess_data_file is None:
            print(f'UnitSpikeTimes import failed for: {animal_id} - {date_of_experiment}')
            return
        nwb = h5.File(os.path.join(sess_data_dir, sess_data_file), 'r')
        # ------ Spike ------
        ec_event_waveform = nwb['processing']['extracellular_units']['EventWaveform']
        ec_unit_times = nwb['processing']['extracellular_units']['UnitTimes']
        # - unit cell type
        cell_type = {}
        for tmp_str in ec_unit_times.get('cell_types').value:
            tmp_str = tmp_str.decode('UTF-8')
            split_str = re.split(' - ', tmp_str)
            cell_type[split_str[0]] = split_str[1]
        # - unit info
        # print('Inserting spike unit: ', end = "")
        for unit_str in tqdm.tqdm(ec_event_waveform.keys()):
            unit_id = int(re.search('\d+', unit_str).group())
            unit_depth = ec_unit_times.get(unit_str).get('depth').value
            key['unit_id'] = unit_id
            key['channel_id'] = ec_event_waveform.get(unit_str).get('electrode_idx').value.item(
                0) - 1  # TODO: check if electrode_idx has MATLAB 1-based indexing (starts at 1)
            key['spike_times'] = ec_unit_times.get(unit_str).get('times').value
            key['unit_cell_type'] = cell_type[unit_str]
            key.update(zip(('unit_x', 'unit_y', 'unit_z'), unit_depth))
            key['spike_waveform'] = ec_event_waveform.get(unit_str).get('data').value
            self.insert1(key)
        #     print(f'{unit_id} ', end = "")
        # print('')
        nwb.close()


@schema
class VMVALUnit(dj.Computed):
    definition = """  # units in the ventral-medial/ventral-anterior-lateral of the thalamus
    -> UnitSpikeTimes    
    ---
    in_vmval: bool
    """

    vm_center = (0.95, -4.33, -1.5)
    dis_threshold = 0.4  # mm

    key_source = UnitSpikeTimes & ProbeInsertion & 'brain_region = "Thalamus"'

    def make(self, key):
        uloc = (UnitSpikeTimes & key).fetch1('unit_x', 'unit_y', 'unit_z')
        dist = np.linalg.norm(np.array(uloc) - np.array(self.vm_center))
        self.insert1(dict(key, in_vmval=bool(dist <= self.dis_threshold)))


@schema
class TrialSegmentedUnitSpikeTimes(dj.Computed):
    definition = """
    -> UnitSpikeTimes
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_spike_times: longblob
    """

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get event time
        try:
            event_time_point = analysis.get_event_time(event_name, key)
        except analysis.EventChoiceError as e:
            print(f'Trial segmentation error - Msg: {str(e)}')
            return

        pre_stim_dur = float(pre_stim_dur)
        post_stim_dur = float(post_stim_dur)
        # check if pre/post stim dur is within start/stop time
        trial_start, trial_stop = (acquisition.TrialSet.Trial & key).fetch1('start_time', 'stop_time')
        if event_time_point - pre_stim_dur < trial_start:
            print('Warning: Out of bound prestimulus duration, set to 0')
            pre_stim_dur = 0
        if event_time_point + post_stim_dur > trial_stop:
            print('Warning: Out of bound poststimulus duration, set to trial end time')
            post_stim_dur = trial_stop - event_time_point

        # get raw & segment
        spike_times = (UnitSpikeTimes & key).fetch1('spike_times')
        key['segmented_spike_times'] = spike_times[np.logical_and(
            (spike_times >= (event_time_point - pre_stim_dur)),
            (spike_times <= (event_time_point + post_stim_dur)))] - event_time_point

        self.insert1(key)
        print(f'Perform trial-segmentation of spike times for unit: {key["unit_id"]} and trial: {key["trial_id"]}')
