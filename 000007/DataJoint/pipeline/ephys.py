'''
Schema of session information.
'''
import datajoint as dj
from . import reference, acquisition, behavior
from . import get_trials, get_spk_times, get_spk_counts, get_psth
import scipy.io as sio
import scipy.stats as ss
import numpy as np
from numpy import random
import os
import glob
import re
from datetime import datetime

schema = dj.schema('gao2018_ephys')


@schema
class ProbeInsertion(dj.Manual):
    definition = """ # Description of probe insertion details during extracellular recording
    -> acquisition.Session
    -> reference.BrainLocation
    ---
    -> reference.Probe
    rec_coordinate_ap: float      # in mm, positive when more anterior relative to the reference point.
    rec_coordinate_ml: float      # in mm, larger when more lateral
    rec_coordinate_dv=null: float # in mm, larger when deeper
    ground_coordinate_ap: float   # in mm
    ground_coordinate_ml: float   # in mm
    ground_coordinate_dv: float   # in mm
    rec_marker: enum('stereotaxic')
    spike_sorting_method: enum('manual')
    ad_unit: varchar(12)
    -> reference.CoordinateReference
    penetration_num: tinyint      # the number of penetration a craniotomy has experienced.
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


@schema
class UnitSpikeTimes(dj.Imported):
    definition = """
    -> ProbeInsertion
    unit_id : smallint
    ---
    -> reference.Probe.Channel.proj(channel = 'channel_id')
    spike_times: longblob  # (s) time of each spike, with respect to the start of session
    spike_trials: longblob # which trial each spike belongs to.
    unit_cell_type='unknown': varchar(32)  # e.g. cell-type of this unit (e.g. wide width, narrow width spiking)
    spike_waveform: longblob  # waveform(s) of each spike at each spike time (spike_time x waveform_timestamps)
    unit_x=null: float  # (mm)
    unit_y=null: float  # (mm)
    unit_z=null: float  # (mm)
    """
    key_source = ProbeInsertion()

    def make(self, key):
        print(key)

        session_dir = (acquisition.Session & key).fetch1('session_directory')
        data = sio.loadmat(session_dir, struct_as_record=False,
                           squeeze_me=True)['obj']

        for iunit, unit in enumerate(data.eventSeriesHash.value):
            value = data.eventSeriesHash.value[iunit]

            # insert the channel entry into the table reference.Probe.Channel
            probe_type = (ProbeInsertion & key).fetch1('probe_type')
            channel = np.unique(value.channel)[0]
            probe_channel = {
                'probe_type': probe_type,
                'channel_id': channel
            }
            reference.Probe.Channel.insert1(probe_channel,
                                            skip_duplicates=True)

            key.update({
                'unit_id': iunit,
                'spike_times': value.eventTimes,
                'spike_trials': value.eventTrials,
                'probe_type': probe_type,
                'channel': channel,
                'spike_waveform': value.waveforms
            })

            if np.size(value.cellType):
                key['unit_cell_type'] = value.cellType

            self.insert1(key)


@schema
class UnitSelectivity(dj.Computed):
    definition = """
    -> UnitSpikeTimes
    -> behavior.TrialCondition
    ---
    r_trial_number:             int         # trial number of right reports
    l_trial_number:             int         # trial number of left reports
    r_trial_ids:                blob        # trial ids of right report trials
    l_trial_ids:                blob        # trial ids of left report trials
    sample_selectivity:         boolean     # whether selectivity is significant during the sample period
    delay_selectivity:          boolean     # whether selectivity is significant during the delay period
    response_selectivity:       boolean     # whether selectivity is significant during the response period
    selectivity:                boolean     # whether any of the previous three is significant
    preference:                 enum('R', 'L', 'N')
    time_window:                blob        # time window of interest
    bins:                       longblob    # time bins
    trial_ids_screened_r:       blob        # trial ids that were screened to calculate the preference, for r trials
    trial_ids_screened_l:       blob        # trial ids that were screened to calculate the preference, for l trials
    mean_fr_r_all:              blob        # mean firing rate of right reporting trials in different stages
    mean_fr_l_all:              blob        # mean firing rate of left reporting trials in different stages
    mean_fr_diff_rl_all:        blob        # mean firing rate difference, right - left
    mean_fr_all:                blob        # mean firing of all trials in different stages
    psth_r_test:                longblob    # psth for right report test trials
    psth_l_test:                longblob    # psth for left report test trials
    psth_prefer_test:           longblob    # psth on preferred test trials
    psth_non_prefer_test:       longblob    # psth on non-preferred test trials
    psth_diff_test:             longblob    # psth difference between preferred and non-preferred test trials
    preference:                 enum('R', 'L', 'No')
    """

    key_source = UnitSpikeTimes * behavior.TrialCondition - \
        (UnitSpikeTimes.proj() &
         (behavior.TrialSetType & 'trial_set_type="photo inhibition"')) * \
        (behavior.TrialCondition & 'trial_condition="Hit"')

    def make(self, key):

        selectivity = key.copy()
        key_no_stim = key.copy()
        key_no_stim['photo_stim_id'] = '0'

        spk_times, spk_trials = (UnitSpikeTimes & key).fetch1(
                'spike_times', 'spike_trials')

        min_trial = np.min(spk_trials)
        max_trial = np.max(spk_trials)

        r_trials = get_trials(key_no_stim, min_trial, max_trial, 'R')
        l_trials = get_trials(key_no_stim, min_trial, max_trial, 'L')
        all_trials = get_trials(key_no_stim, min_trial, max_trial, 'All')

        if not (len(l_trials) > 8 and len(r_trials) > 8):
            return

        r_trial_ids = r_trials.fetch('trial_id')
        l_trial_ids = l_trials.fetch('trial_id')
        all_trial_ids = all_trials.fetch('trial_id')

        # spike times
        spk_times_r = get_spk_times(key, spk_times, spk_trials,
                                    r_trial_ids)
        spk_times_l = get_spk_times(key, spk_times, spk_trials,
                                    l_trial_ids)
        spk_times_all = get_spk_times(key, spk_times, spk_trials,
                                      all_trial_ids)

        # spike counts in different stages
        spk_counts_r = np.array(get_spk_counts(key, spk_times_r, r_trial_ids))
        spk_counts_l = np.array(get_spk_counts(key, spk_times_l, l_trial_ids))
        spk_counts_all = np.array(get_spk_counts(key, spk_times_all, all_trial_ids))

        mean_fr_r = np.mean(spk_counts_r, axis=0)
        mean_fr_l = np.mean(spk_counts_l, axis=0)
        mean_fr_all = np.mean(spk_counts_all, axis=0)

        # check selectivity
        result_sample = ss.ttest_ind(spk_counts_r[:, 0],
                                     spk_counts_l[:, 0])
        result_delay = ss.ttest_ind(spk_counts_r[:, 1],
                                    spk_counts_l[:, 1])
        result_response = ss.ttest_ind(spk_counts_r[:, 2],
                                       spk_counts_l[:, 2])
        sample_selectivity = int(result_sample.pvalue < 0.05)
        delay_selectivity = int(result_delay.pvalue < 0.05)
        response_selectivity = int(result_response.pvalue < 0.05)

        # screen size depends on the experimental type
        trial_set_type = (behavior.TrialSetType & key).fetch1('trial_set_type')
        if trial_set_type == "photo activation":
            screen_size = 10
        else:
            screen_size = 5

        random.shuffle(r_trial_ids)
        random.shuffle(l_trial_ids)

        spk_times_r_screen = get_spk_times(key, spk_times, spk_trials,
                                           r_trial_ids[:screen_size])
        mean_fr_r_screen = np.mean(get_spk_counts(key,
                                                  spk_times_r_screen,
                                                  r_trial_ids[:screen_size]),
                                   axis=0)

        spk_times_l_screen = get_spk_times(key, spk_times, spk_trials,
                                           l_trial_ids[:screen_size])
        mean_fr_l_screen = np.mean(get_spk_counts(key,
                                                  spk_times_l_screen,
                                                  l_trial_ids[:screen_size]),
                                   axis=0)

        spk_times_r_test = get_spk_times(key, spk_times, spk_trials,
                                         r_trial_ids[screen_size:])
        spk_counts_r_test = get_spk_counts(key, spk_times_r_test,
                                           r_trial_ids[screen_size:])

        spk_times_l_test = get_spk_times(key, spk_times, spk_trials,
                                         l_trial_ids[screen_size:])
        spk_counts_l_test = get_spk_counts(key, spk_times_l_test,
                                           l_trial_ids[screen_size:])

        # compute convoluted psth
        time_window = [-3.5, 2]
        bins = np.arange(time_window[0], time_window[1]+0.001, 0.001)

        psth_r_test = get_psth(spk_times_r_test, bins)
        psth_l_test = get_psth(spk_times_l_test, bins)
        if mean_fr_r_screen[3] > mean_fr_l_screen[3]:
            psth_prefer_test = psth_r_test
            psth_non_prefer_test = psth_l_test
            preference = 'R'
        else:
            psth_prefer_test = psth_l_test
            psth_non_prefer_test = psth_r_test
            preference = 'L'

        if not selectivity:
            preference = 'No'

        selectivity.update({
            'r_trial_number': len(r_trials),
            'l_trial_number': len(l_trials),
            'r_trial_ids': r_trial_ids,
            'l_trial_ids': l_trial_ids,
            'sample_selectivity': sample_selectivity,
            'delay_selectivity':  delay_selectivity,
            'response_selectivity': response_selectivity,
            'selectivity': int(np.any([sample_selectivity, delay_selectivity,
                                       response_selectivity])),
            'time_window': time_window,
            'bins': bins,
            'trial_ids_screened_r': r_trial_ids[:screen_size],
            'trial_ids_screened_l': l_trial_ids[:screen_size],
            'psth_r_test': psth_r_test,
            'psth_l_test': psth_l_test,
            'psth_prefer_test': psth_prefer_test,
            'psth_non_prefer_test': psth_non_prefer_test,
            'psth_diff_test': psth_prefer_test - psth_non_prefer_test,
            'mean_fr_r_all': mean_fr_r,
            'mean_fr_l_all': mean_fr_l,
            'mean_fr_diff_rl_all': mean_fr_r - mean_fr_l,
            'mean_fr_all': mean_fr_all,
            'preference': preference
        })

        self.insert1(selectivity)


@schema
class AlignedPsthStimOn(dj.Computed):
    definition = """
    -> UnitSelectivity
    -> behavior.PhotoStimType
    ---
    r_trial_number_on:    int         # trial number of right reports
    l_trial_number_on:    int         # trial number of left reports
    mean_fr_r_on:         longblob    # mean firing rate for right report trials
    mean_fr_l_on:         longblob    # mean firing rate for left report trials
    mean_fr_all_on:       longblob    # mean firing rate for all trials
    psth_r_on:            longblob    # psth for right report trials
    psth_l_on:            longblob    # psth for left report trials
    psth_prefer_on:       longblob    # psth on preferred trials
    psth_non_prefer_on:   longblob    # psth on non-preferred trials
    psth_diff_on:         longblob    # psth difference betweens preferred trials and non-preferred trials
    """

    def make(self, key):

        if key['photo_stim_id'] in ['NaN', '0']:
            return

        time_window, bins, preference, selectivity = \
            (UnitSelectivity & key).fetch1(
                'time_window', 'bins', 'preference', 'selectivity')

        if not selectivity:
            return

        aligned_psth = key.copy()

        spk_times, spk_trials = (UnitSpikeTimes & key).fetch1(
            'spike_times', 'spike_trials')
        min_trial = min(spk_trials)
        max_trial = max(spk_trials)
        r_trials = get_trials(key, min_trial, max_trial, 'R')
        l_trials = get_trials(key, min_trial, max_trial, 'L')
        all_trials = get_trials(key, min_trial, max_trial, 'All')

        if not (len(l_trials) > 2 and len(r_trials) > 2):
            return

        r_trial_ids = r_trials.fetch('trial_id')
        l_trial_ids = l_trials.fetch('trial_id')
        all_trial_ids = all_trials.fetch('trial_id')

        # spike times
        spk_times_r = get_spk_times(key, spk_times, spk_trials,
                                    r_trial_ids)
        spk_times_l = get_spk_times(key, spk_times, spk_trials,
                                    l_trial_ids)
        spk_times_all = get_spk_times(key, spk_times, spk_trials,
                                      all_trial_ids)

        # spike counts in different stages
        spk_counts_r = np.array(get_spk_counts(key, spk_times_r, r_trial_ids))
        spk_counts_l = np.array(get_spk_counts(key, spk_times_l, l_trial_ids))
        spk_counts_all = np.array(get_spk_counts(key, spk_times_all, all_trial_ids))

        # compute convoluted psth
        psth_r = get_psth(spk_times_r, bins)
        psth_l = get_psth(spk_times_l, bins)

        if preference == 'R':
            psth_prefer = psth_r
            psth_non_prefer = psth_l
        elif preference == 'L':
            psth_prefer = psth_l
            psth_non_prefer = psth_r

        aligned_psth.update({
            'r_trial_number_on': len(r_trials),
            'l_trial_number_on': len(l_trials),
            'mean_fr_r_on': np.mean(spk_counts_r, axis=0),
            'mean_fr_l_on': np.mean(spk_counts_l, axis=0),
            'mean_fr_all_on': np.mean(spk_counts_all, axis=0),
            'psth_r_on': psth_r,
            'psth_l_on': psth_l,
            'psth_prefer_on': psth_prefer,
            'psth_non_prefer_on': psth_non_prefer,
            'psth_diff_on': psth_prefer - psth_non_prefer
        })

        self.insert1(aligned_psth)


@schema
class PsthForCodingDirection(dj.Computed):
    definition = """
    -> behavior.TrialSet
    """

    key_source = behavior.TrialSet & (
        behavior.TrialNumberSummary &
        'n_sample_l_trials > 5' & 'n_sample_r_trials > 5' &
        'n_delay_l_trials > 5' & 'n_delay_r_trials > 5' &
        'n_no_stim_l_trials > 5' & 'n_no_stim_r_trials > 5'
    )

    def make(self, key):
        self.insert1(key)
        testing_trial_num = (behavior.TrialNumberSummary & key).fetch1('n_test_trials')
        keys_training = []
        keys_stim_off = []
        keys_stim_on = []

        for ikey in (UnitSpikeTimes & key).fetch('KEY'):
            print("Populating {}th unit".format(ikey['unit_id']))
            spk_times, spk_trials = (UnitSpikeTimes & ikey).fetch1(
                'spike_times', 'spike_trials')

            min_trial = np.min(spk_trials)
            max_trial = np.max(spk_trials)

            cond_hit = dict(**ikey, trial_condition='Hit',
                            photo_stim_id='0')
            cond_all = dict(**ikey, trial_condition='All',
                            photo_stim_id='0')

            r_trials_hit = get_trials(cond_hit, min_trial, max_trial, 'R')
            r_trials_all = get_trials(cond_all, min_trial, max_trial, 'R')
            l_trials_hit = get_trials(cond_hit, min_trial, max_trial, 'L')
            l_trials_all = get_trials(cond_all, min_trial, max_trial, 'L')

            r_trial_ids_hit = r_trials_hit.fetch('trial_id')
            l_trial_ids_hit = l_trials_hit.fetch('trial_id')
            r_trial_ids_all = r_trials_all.fetch('trial_id')
            l_trial_ids_all = l_trials_all.fetch('trial_id')

            # training trials only comes from the hit trials
            r_training_trial_ids = list(r_trial_ids_hit[testing_trial_num:])
            l_training_trial_ids = list(l_trial_ids_hit[testing_trial_num:])
            all_training_trial_ids = r_training_trial_ids + l_training_trial_ids

            if len(r_training_trial_ids) < 10 or len(l_training_trial_ids) < 10:
                continue

            # test trials are the rest of all trials, including hit and err
            r_test_trial_ids = [id for id in r_trial_ids_all if id not in r_training_trial_ids]
            l_test_trial_ids = [id for id in l_trial_ids_all if id not in l_training_trial_ids]

            # spike times
            spk_times_r_test = get_spk_times(
                ikey, spk_times, spk_trials, r_test_trial_ids)
            spk_times_r_training = get_spk_times(
                ikey, spk_times, spk_trials, r_training_trial_ids)
            spk_times_l_test = get_spk_times(
                ikey, spk_times, spk_trials, l_test_trial_ids)
            spk_times_l_training = get_spk_times(
                ikey, spk_times, spk_trials, l_training_trial_ids)

            spk_times_all_training = get_spk_times(
                ikey, spk_times, spk_trials, all_training_trial_ids)

            # spike counts for different periods
            spk_counts_r_training = np.array(get_spk_counts(ikey, spk_times_r_training, r_training_trial_ids))
            spk_counts_l_training = np.array(get_spk_counts(ikey, spk_times_l_training, l_training_trial_ids))
            spk_counts_all_training = np.array(get_spk_counts(ikey, spk_times_all_training, all_training_trial_ids))

            # compute psth for no photo stim test trials
            time_window = [-3.5, 2]
            bins = np.arange(time_window[0], time_window[1]+0.001, 0.001)
            psth_r_test = get_psth(spk_times_r_test, bins)
            psth_l_test = get_psth(spk_times_l_test, bins)
            psth_r_training = get_psth(spk_times_r_training, bins)
            psth_l_training = get_psth(spk_times_l_training, bins)
            psth_all_training = get_psth(spk_times_all_training, bins)

            # ingest firing rate for training
            key_training = ikey.copy()
            key_training.update(
                r_training_trial_ids=r_training_trial_ids,
                l_training_trial_ids=l_training_trial_ids,
                mean_fr_l_training=np.mean(spk_counts_l_training, axis=0),
                mean_fr_r_training=np.mean(spk_counts_r_training, axis=0),
                mean_fr_all_training=np.mean(spk_counts_all_training, axis=0),
                spk_times_l_training=spk_times_l_training,
                spk_times_r_training=spk_times_r_training,
                psth_l_training=psth_l_training,
                psth_r_training=psth_r_training,
                psth_all_training=psth_all_training
            )
            keys_training.append(key_training)

            # ingest PSTH test for photo stim off trials
            key_stim_off = ikey.copy()
            key_stim_off.update(
                photo_stim_id="0",
                psth_l_test=psth_l_test,
                psth_r_test=psth_r_test,
                spk_times_l_test=spk_times_l_test,
                spk_times_r_test=spk_times_r_test,
                time_bins=bins
            )
            keys_stim_off.append(key_stim_off)

            # ingest PSTH for photo stim on trials
            photo_stims = dj.U('photo_stim_id') & (behavior.TrialSet.Trial & key & 'photo_stim_id != "0"')
            for photo_stim in photo_stims.fetch('KEY'):
                cond_all = dict(**ikey, trial_condition='All',
                                photo_stim_id=photo_stim['photo_stim_id'])
                r_trials_all = get_trials(cond_all, min_trial, max_trial, 'R')
                l_trials_all = get_trials(cond_all, min_trial, max_trial, 'L')

                r_trial_ids = r_trials_all.fetch('trial_id')
                l_trial_ids = l_trials_all.fetch('trial_id')
                spk_times_r = get_spk_times(
                    ikey, spk_times, spk_trials, r_trial_ids)
                spk_times_l = get_spk_times(
                    ikey, spk_times, spk_trials, l_trial_ids)

                if not (len(spk_times_r) and len(spk_times_l)):
                    continue
                psth_r = get_psth(spk_times_r, bins)
                psth_l = get_psth(spk_times_l, bins)

                key_stim_on = ikey.copy()
                key_stim_on.update(
                    photo_stim_id=photo_stim['photo_stim_id'],
                    psth_l_test=psth_l,
                    psth_r_test=psth_r,
                    spk_times_l_test=spk_times_l,
                    spk_times_r_test=spk_times_r,
                    time_bins=bins
                )
                keys_stim_on.append(key_stim_on)

        self.MeanFiringRateTraining.insert(keys_training)
        self.PsthTest.insert(keys_stim_off)
        self.PsthTest.insert(keys_stim_on)

    class MeanFiringRateTraining(dj.Part):
        definition = """
        -> master
        -> UnitSpikeTimes
        ---
        r_training_trial_ids:    longblob
        l_training_trial_ids:    longblob
        mean_fr_l_training:      blob     # mean firing rate across trials for different stages
        mean_fr_r_training:      blob     # mean firing rate across trials for different stages
        mean_fr_all_training:    blob     # mean firing rate across trials for different stages
        spk_times_l_training:    longblob
        spk_times_r_training:    longblob
        psth_l_training:         blob     # psth of left training trials
        psth_r_training:         blob     # psth of right training trials
        psth_all_training:       blob     # psth of all training trials
        """

    class PsthTest(dj.Part):
        definition = """
        -> master.MeanFiringRateTraining
        -> behavior.PhotoStimType
        ---
        psth_l_test:      longblob
        psth_r_test:      longblob
        time_bins:        longblob
        spk_times_l_test: longblob
        spk_times_r_test: longblob
        """


@schema
class CodingDirection(dj.Computed):
    definition = """
    -> PsthForCodingDirection
    ---
    coding_direction: longblob  # unit_number x 1, normalized difference r-l
    """

    def make(self, key):
        mean_fr_l, mean_fr_r = (PsthForCodingDirection.MeanFiringRateTraining &
                                (UnitSpikeTimes & 'unit_cell_type="pyramidal"') &
                                key).fetch(
            'mean_fr_l_training', 'mean_fr_r_training')
        cd_vec = [fr_r[1] - fr_l[1] for fr_r, fr_l in zip(mean_fr_r, mean_fr_l)]
        key['coding_direction'] = cd_vec / np.linalg.norm(cd_vec)

        self.insert1(key)


@schema
class ProjectedPsthTraining(dj.Computed):
    definition = """
    -> PsthForCodingDirection
    ---
    proj_psth_training:   longblob
    mean_fr_training:     float
    """
    key_source = PsthForCodingDirection & PsthForCodingDirection.MeanFiringRateTraining

    def make(self, key):
        psth = (PsthForCodingDirection.MeanFiringRateTraining &
                (UnitSpikeTimes & 'unit_cell_type="pyramidal"') & key).fetch(
            'psth_all_training')
        cd = (CodingDirection & key).fetch1('coding_direction')
        key.update(
            proj_psth_training=np.dot(psth, cd)
        )
        key.update(
            mean_fr_training=np.mean(key['proj_psth_training'])
        )
        self.insert1(key)


@schema
class ProjectedPsth(dj.Computed):
    definition = """
    -> PsthForCodingDirection
    -> behavior.PhotoStimType
    ---
    proj_psth_l:   longblob
    proj_psth_r:   longblob
    """
    key_source = (PsthForCodingDirection * behavior.PhotoStimType).proj() & PsthForCodingDirection.PsthTest

    def make(self, key):
        psth_l, psth_r = (PsthForCodingDirection.PsthTest & (UnitSpikeTimes & 'unit_cell_type="pyramidal"') & key).fetch(
            'psth_l_test', 'psth_r_test')
        cd = (CodingDirection & key).fetch1('coding_direction')
        mean_fr_training = (ProjectedPsthTraining & key).fetch1(
            'mean_fr_training')
        key.update(
            proj_psth_l=np.dot(psth_l, cd) - mean_fr_training,
            proj_psth_r=np.dot(psth_r, cd) - mean_fr_training
        )
        self.insert1(key)
