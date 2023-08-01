'''
Schema of behavior information.
'''
import datajoint as dj
from pipeline import reference, acquisition
import scipy.io as sio
import numpy as np
import os
import glob
import re
from datetime import datetime

schema = dj.schema('gao2018_behavior')


@schema
class PhotoStimType(dj.Lookup):
    definition = """
    photo_stim_id: varchar(8)
    ---
    -> [nullable] reference.BrainLocation
    -> [nullable] reference.Hemisphere
    photo_stim_period='':               varchar(24)  # period during the trial
    photo_stim_relative_location='':    varchar(24)  # stimulus location relative to the recording.
    photo_stim_act_type='':             varchar(24)  # excitation or inihibition
    photo_stim_duration=0:              float        # in ms, stimulus duration
    photo_stim_shape='':                varchar(24)  # shape of photostim, cosine or pulsive
    photo_stim_freq=0:                  float        # in Hz, frequency of photostimulation
    photo_stim_notes='':                varchar(128)
    """

    contents = [
        ['0', None, None, '', '', '', 0, '', 0, 'no stimulus'],
        ['1', 'Fastigial', 'right', 'sample', 'contralateral', 'activation',
            500, '5ms pulse', 20, ''],
        ['2', 'Fastigial', 'right', 'delay', 'contralateral', 'activation',
            500, '5ms pulse', 20, ''],
        ['3', 'Dentate', 'right', 'sample', 'contralateral', 'activation',
            500, '5ms pulse', 20, ''],
        ['4', 'Dentate', 'right', 'delay', 'contralateral', 'activation',
            500, '5ms pulse', 20, ''],
        ['5', 'DCN', 'right', 'delay', 'contralateral', 'inhibition',
            500, 'cosine', 40, ''],
        ['6', 'DCN', 'right', 'delay', 'contralateral', 'inhibition',
            500, 'cosine', 40, ''],
        ['NaN', None, None, '', '', '', 0, '', 0, 'stimulation configuration \
            for other purposes, should not analyze']
    ]


@schema
class TrialSet(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    number_of_trials:   int         # number of trials in this session.
    """

    def make(self, key):
        trial_result = key.copy()
        session_dir = (acquisition.Session & key).fetch1('session_directory')
        data = sio.loadmat(session_dir, struct_as_record=False,
                           squeeze_me=True)['obj']

        key.update({'number_of_trials': len(data.trialStartTimes)})
        self.insert1(key)

        trial_type_str = data.trialTypeStr[:-2]
        trial_idx = data.timeSeriesArrayHash.value.trial

        for idx, itrial in enumerate(data.trialIds):

            trial_type_vec = np.squeeze(data.trialTypeMat[:6, idx])
            trial_type = trial_type_str[np.array(trial_type_vec, dtype=bool)]

            if len(trial_type) == 0:
                trial_type = 'NoLickNoResponse'
            else:
                trial_type = trial_type[0]

            pole_in_time = data.trialPropertiesHash.value[0][idx]
            pole_out_time = data.trialPropertiesHash.value[1][idx]
            cue_time = data.trialPropertiesHash.value[2][idx]
            good_trial = data.trialPropertiesHash.value[3][idx]
            photo_stim_type = data.trialPropertiesHash.value[4][idx]

            if np.any(np.isnan(cue_time)):
                continue

            if np.size(cue_time) > 1:
                cue_time = cue_time[0]

            if np.any(np.isnan([pole_in_time, pole_out_time,
                                photo_stim_type])) or good_trial == 0:
                continue

            itrial_idx = np.squeeze(np.where(trial_idx == itrial))
            if not itrial_idx.size:
                return

            trial_result.update({
                'trial_id': itrial,
                'trial_start_time': data.trialStartTimes[idx],
                'trial_pole_in_time': pole_in_time,
                'trial_pole_out_time': pole_out_time,
                'trial_cue_time': cue_time,
                'trial_response': trial_type,
                'trial_lick_early': bool(data.trialTypeMat[6][idx]),
                'photo_stim_id': str(int(photo_stim_type)),
                'trial_start_idx': itrial_idx[0],
                'trial_end_idx': itrial_idx[-1]
            })
            self.Trial().insert1(trial_result)

    class Trial(dj.Part):
        definition = """
        -> master
        trial_id: int     # trial number to reference to the trials
        ---
        trial_start_time:       float           # in secs, time referenced to session start
        trial_pole_in_time:     float           # in secs, the start of the sample period for each trial, relative to the trial start
        trial_pole_out_time:    float           # in secs, the end of the sample period and start of the delay period, relative to the trial start
        trial_cue_time:         float           # in secs, the end of the delay period, relative to the start of the trials
        trial_response:         enum('HitR', 'HitL', 'ErrR', 'ErrL', 'NoLickR', 'NoLickL', 'NoLickNoResponse')  # subject response to the stimulus
        trial_lick_early:       boolean         # whether the animal licks early
        -> PhotoStimType
        trial_start_idx:        int             # first index for this trial, on the session recording series
        trial_end_idx:          int             # last index for this trial, on the session recording series
        """


@schema
class TrialCondition(dj.Lookup):
    definition = """
    trial_condition: varchar(8)   # name of this condition
    """
    contents = zip(['Hit', 'All'])


@schema
class TrialSetType(dj.Computed):
    definition = """
    -> TrialSet
    ---
    trial_set_type: enum('photo activation', 'photo inhibition')
    """

    def make(self, key):
        activation = TrialSet.Trial & key & \
            (PhotoStimType & 'photo_stim_act_type="activation"')
        inhibition = TrialSet.Trial & key & \
            (PhotoStimType & 'photo_stim_act_type="inhibition"')

        if len(activation):
            key['trial_set_type'] = 'photo activation'

        if len(inhibition):
            key['trial_set_type'] = 'photo inhibition'

        self.insert1(key)


@schema
class TrialNumberSummary(dj.Computed):
    definition = """
    -> TrialSet
    ---
    n_sample_l_trials   :   int
    n_sample_r_trials   :   int
    n_delay_l_trials    :   int
    n_delay_r_trials    :   int
    n_no_stim_l_trials  :   int
    n_no_stim_r_trials  :   int
    n_test_trials       :   int
    """
    key_source = TrialSet & (
        TrialSet.Trial & 'photo_stim_id in ("1","2","3","4")')

    def make(self, key):
        key.update(
            n_sample_l_trials=len(TrialSet.Trial & key & 'photo_stim_id in ("1","3")' & 'trial_response in ("HitL", "ErrL")'),
            n_sample_r_trials=len(TrialSet.Trial & key & 'photo_stim_id in ("1","3")' & 'trial_response in ("HitR", "ErrR")'),
            n_delay_l_trials=len(TrialSet.Trial & key & 'photo_stim_id in ("2","4")' & 'trial_response in ("HitL", "ErrL")'),
            n_delay_r_trials=len(TrialSet.Trial & key & 'photo_stim_id in ("2","4")' & 'trial_response in ("HitR", "ErrR")'),
            n_no_stim_l_trials=len(TrialSet.Trial & key & 'photo_stim_id="0"' & 'trial_response in ("HitL", "ErrL")'),
            n_no_stim_r_trials=len(TrialSet.Trial & key & 'photo_stim_id="0"' & 'trial_response in ("HitR", "ErrR")'),
        )

        key['n_test_trials'] = np.mean([key['n_sample_l_trials'],
                                        key['n_sample_r_trials'],
                                        key['n_delay_l_trials'],
                                        key['n_delay_r_trials']])
        self.insert1(key)
