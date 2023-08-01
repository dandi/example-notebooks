
import numpy as np
import scipy.signal as signal


# helper functions
def get_trials(key, min_trial, max_trial, trial_type):

    if trial_type == 'All':
        if key['trial_condition'] == 'All':
            query = {}
        elif key['trial_condition'] == 'Hit':
            query = 'trial_response in ("HitL", "HitR")'
    else:
        if key['trial_condition'] == 'All':
            query = f'trial_response in ("Hit{trial_type}", "Err{trial_type}")'
        elif key['trial_condition'] == 'Hit':
            query = f'trial_response = "Hit{trial_type}"'

    return behavior.TrialSet.Trial & key & query & \
        'trial_lick_early = 0' & \
        'trial_id between {} and {}'.format(min_trial, max_trial)


def get_spk_times(key, spk_times, spk_trials, trials):
    return [spk_times[spk_trials == trial] -
            (behavior.TrialSet.Trial & key &
                'trial_id = {}'.format(trial)).proj(
                    cue_time='trial_cue_time + trial_start_time').fetch1(
                        'cue_time')
            for trial in trials]


def get_spk_counts(key, spk_times, trials):

    spk_counts = []
    for itrial, trial in enumerate(trials):
        pole_in_time, pole_out_time = \
            (behavior.TrialSet.Trial & key &
                'trial_id = {}'.format(trial)).proj(
                    pole_in_time='trial_pole_in_time - trial_cue_time',
                    pole_out_time='trial_pole_out_time - trial_cue_time'
            ).fetch1('pole_in_time', 'pole_out_time')

        after_cue_time = 1.3
        before_pole_in_time = 0.5
        spk_time = spk_times[itrial]

        spk_counts.append([])

        spk_counts[itrial].append([])
        # spk counts (spks/sec) in the sampling period
        spk_counts[itrial][0] = \
            sum((spk_time < pole_out_time) & (spk_time > pole_in_time)) / \
            (pole_out_time - pole_in_time)

        spk_counts[itrial].append([])
        # spk counts (spks/sec) in the delay period
        spk_counts[itrial][1] = \
            sum((spk_time < 0) & (spk_time > pole_out_time)) / \
            (0 - pole_out_time)

        spk_counts[itrial].append([])
        # spk counts (spks/sec) in the response period (0 to 1.3s after cue)
        spk_counts[itrial][2] = \
            sum((spk_time < after_cue_time) & (spk_time > 0)) / after_cue_time

        # spk counts (spks/sec) in the entire period (from pole in to 1.3s
        # after cue)
        spk_counts[itrial].append([])
        spk_counts[itrial][3] = \
            sum((spk_time < after_cue_time) & (spk_time > pole_in_time)) / \
            (after_cue_time - pole_in_time)

        # spk counts (spks/sec) in the pre-pole in period (-0.5s to pole_in
        # time)
        spk_counts[itrial].append([])
        spk_counts[itrial][4] = \
            sum((spk_time < pole_in_time) &
                (spk_time > pole_in_time - before_pole_in_time)) / \
            before_pole_in_time

    return spk_counts


def get_psth(spk_times, time_bins):

    mean_counts = np.divide(
        np.histogram(np.hstack(spk_times),
                     range=[min(time_bins), max(time_bins)],
                     bins=len(time_bins))[0],
        len(spk_times))

    # convolve with a box-car filter
    window_size = 200
    dt = np.mean(np.diff(time_bins))
    return np.divide(signal.convolve(mean_counts, signal.boxcar(window_size), mode='same'),
                     window_size*dt)
