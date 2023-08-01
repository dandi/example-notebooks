'''
Schema of intracellular information.
'''

import os
import pathlib
import numpy as np
import datajoint as dj
import h5py as h5

from . import utilities, analysis

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'intracellular')

sess_data_dir = pathlib.Path(dj.config['custom'].get('intracellular_directory')).as_posix()


@schema
class Cell(dj.Manual):
    definition = """ # A cell undergone intracellular recording in this session
    -> acquisition.Session
    cell_id: varchar(36) # a string identifying the cell in which this intracellular recording is concerning
    ---
    cell_type: enum('excitatory','inhibitory','N/A')
    -> reference.ActionLocation
    -> reference.WholeCellDevice
    """


@schema
class MembranePotential(dj.Imported):
    definition = """
    -> Cell
    ---
    membrane_potential: longblob    # (mV) membrane potential recording at this cell
    membrane_potential_wo_spike: longblob # (mV) membrane potential without spike data, derived from membrane potential recording    
    membrane_potential_start_time: float # (s) first timepoint of membrane potential recording
    membrane_potential_sampling_rate: float # (Hz) sampling rate of membrane potential recording
    """

    def make(self, key):
        # ============ Dataset ============
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
        # Search the files in filenames to find a match for "this" session (based on key)
        sess_data_file = utilities.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
        if sess_data_file is None:
            raise FileNotFoundError(f'IntracellularAcquisition import failed for: {animal_id} - {date_of_experiment}')
        nwb = h5.File(os.path.join(sess_data_dir, sess_data_file), 'r')
        #  ============= Now read the data and start ingesting =============
        print('Insert intracellular data for: subject: {0} - date: {1} - cell: {2}'.format(key['subject_id'],
                                                                                           key['session_time'],
                                                                                           key['cell_id']))
        # -- MembranePotential
        membrane_potential_time_stamps = nwb['acquisition']['timeseries']['membrane_potential']['timestamps'].value
        self.insert1(dict(key,
                          membrane_potential=nwb['acquisition']['timeseries']['membrane_potential'][
                              'data'].value,
                          membrane_potential_wo_spike=
                          nwb['analysis']['Vm_wo_spikes']['membrane_potential_wo_spike'][
                              'data'].value,
                          membrane_potential_start_time=membrane_potential_time_stamps[0],
                          membrane_potential_sampling_rate=1 / np.mean(
                              np.diff(membrane_potential_time_stamps))))
        nwb.close()


@schema
class CurrentInjection(dj.Imported):
    definition = """
    -> Cell
    ---
    current_injection: longblob
    current_injection_start_time: float  # first timepoint of current injection recording
    current_injection_sampling_rate: float  # (Hz) sampling rate of current injection recording
    """

    def make(self, key):
        # ============ Dataset ============
        # Get the Session definition from the keys of this session
        animal_id = key['subject_id']
        date_of_experiment = key['session_time']
        # Search the files in filenames to find a match for "this" session (based on key)
        sess_data_file = utilities.find_session_matched_nwbfile(sess_data_dir, animal_id, date_of_experiment)
        if sess_data_file is None:
            raise FileNotFoundError(f'IntracellularAcquisition import failed for: {animal_id} - {date_of_experiment}')
        nwb = h5.File(os.path.join(sess_data_dir, sess_data_file), 'r')
        #  ============= Now read the data and start ingesting =============
        print('Insert intracellular data for: subject: {0} - date: {1} - cell: {2}'.format(key['subject_id'],
                                                                                           key['session_time'],
                                                                                           key['cell_id']))
        # -- CurrentInjection
        current_injection_time_stamps = nwb['acquisition']['timeseries']['current_injection']['timestamps'].value
        self.insert1(dict(key,
                                           current_injection = nwb['acquisition']['timeseries']['current_injection'][
                                               'data'].value,
                                           current_injection_start_time = current_injection_time_stamps[0],
                                           current_injection_sampling_rate = 1 / np.mean(
                                               np.diff(current_injection_time_stamps))))
        nwb.close()


@schema
class TrialSegmentedMembranePotential(dj.Computed):
    definition = """
    -> MembranePotential
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_mp: longblob   
    segmented_mp_wo_spike: longblob
    """

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        fs, first_time_point, Vm_wo_spike, Vm_w_spike = (MembranePotential & key).fetch1(
            'membrane_potential_sampling_rate', 'membrane_potential_start_time', 'membrane_potential_wo_spike',
            'membrane_potential')
        # segmentation
        segmented_Vm_wo_spike = analysis.perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur,
                                                                    Vm_wo_spike, fs, first_time_point)
        segmented_Vm_w_spike = analysis.perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur,
                                                                   Vm_w_spike, fs, first_time_point)
        self.insert1(dict(key,
                          segmented_mp = segmented_Vm_w_spike,
                          segmented_mp_wo_spike = segmented_Vm_wo_spike))
        print(f'Perform trial-segmentation of membrane potential for trial: {key["trial_id"]}')


@schema
class TrialSegmentedCurrentInjection(dj.Computed):
    definition = """
    -> CurrentInjection
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_current_injection: longblob
    """

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        fs, first_time_point, current_injection = (CurrentInjection & key).fetch1(
            'current_injection_sampling_rate', 'current_injection_start_time', 'current_injection')
        segmented_current_injection = analysis.perform_trial_segmentation(key, event_name, pre_stim_dur, post_stim_dur,
                                                                          current_injection, fs, first_time_point)
        self.insert1(dict(key, segmented_current_injection = segmented_current_injection))
        print(f'Perform trial-segmentation of current injection for trial: {key["trial_id"]}')
