'''
Schema of stimulation information.
'''
import re
import os
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj

from . import reference, subject, utilities, acquisition, analysis

schema = dj.schema(dj.config['custom']['database.prefix'] + 'stimulation')


@schema
class PhotoStimDevice(dj.Lookup):
    definition = """ # Information about the devices used for photo stimulation
    device_name: varchar(32)
    ---
    device_desc = "": varchar(1024)
    """   
    

@schema
class PhotoStimProtocol(dj.Manual):
    definition = """
    protocol: varchar(16)
    ---
    -> PhotoStimDevice
    photo_stim_excitation_lambda: decimal(6,2)    # (nm) excitation wavelength
    photo_stim_method = 'laser' : enum('fiber', 'laser')
    photo_stim_duration = null:                float        # (ms), stimulus duration
    photo_stim_shape = '':                   varchar(24)  # shape of photostim, cosine or pulsive
    photo_stim_freq = null:                    float        # (Hz), frequency of photostimulation
    photo_stim_notes = '':                varchar(1024)
    """


@schema
class PhotoStimulation(dj.Manual):
    definition = """  #  Photostimulus profile used for stimulation in this session
    -> acquisition.Session
    photostim_id: varchar(12)  # identification of this stimulation, in the scenario of multiple stimulations per session
    ---
    -> reference.ActionLocation
    -> PhotoStimProtocol
    photostim_timeseries=null: longblob  # (mW)
    photostim_timestamps=null: longblob  # (s) 
    """


@schema
class TrialPhotoStimParam(dj.Imported):
    definition = """ # information related to the stimulation settings for this trial
    -> acquisition.TrialSet.Trial
    ---
    photo_stim_mode: varchar(16)
    photo_stim_power=null: float  # (mW) stimulation power 
    """

    def make(self, key):
        # this function implements the ingestion of Trial stim info into the pipeline
        return None


@schema
class TrialSegmentedPhotoStimulus(dj.Computed):
    definition = """
    -> PhotoStimulation
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_photostim: longblob
    """

    # custom key_source where acquisition.PhotoStimulation.photostim_timeseries exist
    key_source = acquisition.TrialSet.Trial * analysis.TrialSegmentationSetting * (
                PhotoStimulation - 'photostim_timeseries is NULL')

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        fs, first_time_point, photostim_timeseries = (PhotoStimulation & key).fetch1(
            'photostim_sampling_rate', 'photostim_start_time', 'photostim_timeseries')
        # segmentation
        try:
            key['segmented_photostim'] = analysis.perform_trial_segmentation(key, event_name, pre_stim_dur,
                                                                             post_stim_dur, photostim_timeseries,
                                                                             fs, first_time_point)
        except analysis.EventChoiceError as e:
            print(f'Trial segmentation error - Msg: {str(e)}')
            return

        self.insert1(key)
        print(f'Perform trial-segmentation of photostim for trial: {key["trial_id"]}')
