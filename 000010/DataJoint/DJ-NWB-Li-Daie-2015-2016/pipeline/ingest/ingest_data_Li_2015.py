import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import re
import scipy.io as sio
from tqdm import tqdm
import pathlib
from decimal import Decimal
import numpy as np

from pipeline import experiment, ephys, tracking
from pipeline import parse_date, time_unit_conversion_factor


def main(data_dir='./data/data_structure'):
    data_dir = pathlib.Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f'Path not found!! {data_dir.as_posix()}')

    # ==================== DEFINE CONSTANTS =====================

    session_suffixes = ['a', 'b', 'c', 'd', 'e']

    trial_type_str = ['HitR', 'HitL', 'ErrR', 'ErrL', 'NoLickR', 'NoLickL']
    trial_type_mapper = {'HitR': ('hit', 'right'),
                         'HitL': ('hit', 'left'),
                         'ErrR': ('miss', 'right'),
                         'ErrL': ('miss', 'left'),
                         'NoLickR': ('ignore', 'right'),
                         'NoLickL': ('ignore', 'left')}

    photostim_mapper = {1: 'PONS', 2: 'ALM'}

    photostim_dur = Decimal('1.3')

    cell_type_mapper = {'pyramidal': 'Pyr', 'FS': 'FS', 'IT': 'IT', 'PT': 'PT'}

    post_resp_tlim = 2  # a trial may last at most 2 seconds after response cue

    task_protocol = {'task': 'audio delay', 'task_protocol': 1}

    clustering_method = 'manual'

    project_name = 'li2015'
    
    insert_kwargs = {'ignore_extra_fields': True, 'allow_direct_insert': True, 'skip_duplicates': True}

    # ================== INGESTION OF DATA ==================
    data_files = data_dir.glob('*.mat')

    for data_file in data_files:
        print(f'-- Read {data_file} --')

        fname = data_file.stem
        subject_id = int(re.search('ANM\d+', fname).group().replace('ANM', ''))
        session_date = parse_date(re.search('_\d+', fname).group().replace('_', ''))

        sessions = (experiment.Session & (experiment.ProjectSession & {'project_name': project_name})
                    & {'subject_id': subject_id, 'session_date': session_date})
        if len(sessions) < 2:
            session_key = sessions.fetch1('KEY')
        else:
            if fname[-1] in session_suffixes:
                sess_num = sessions.fetch('session', order_by='session')
                session_letter_mapper = {letter: s_no for letter, s_no in zip(session_suffixes, sess_num)}
                session_key = (sessions & {'session': session_letter_mapper[fname[-1]]}).fetch1('KEY')
            else:
                raise Exception(f'Multiple sessions found for {fname}')

        print(f'\tMatched: {session_key}')

        if ephys.TrialSpikes & session_key:
            print('Data ingested, skipping over...')
            continue

        sess_data = sio.loadmat(data_file, struct_as_record = False, squeeze_me=True)['obj']

        # get time conversion factor - (-1) to take into account Matlab's 1-based indexing
        ts_time_conversion = time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.timeSeriesArrayHash.value.timeUnit - 1]]
        trial_time_conversion = time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.trialTimeUnit - 1]]
        unit_time_converstion = time_unit_conversion_factor[
            sess_data.timeUnitNames[sess_data.eventSeriesHash.value[0].timeUnit - 1]]

        # ---- time-series data ----
        ts_tvec = sess_data.timeSeriesArrayHash.value.time * ts_time_conversion
        ts_trial = sess_data.timeSeriesArrayHash.value.trial
        lick_trace = sess_data.timeSeriesArrayHash.value.valueMatrix[:, 0]
        aom_input_trace = sess_data.timeSeriesArrayHash.value.valueMatrix[:, 1]
        laser_power = sess_data.timeSeriesArrayHash.value.valueMatrix[:, 2]

        # ---- trial data ----
        photostims = (experiment.Photostim * experiment.PhotostimBrainRegion & session_key)

        trial_zip = zip(sess_data.trialIds, sess_data.trialStartTimes * trial_time_conversion,
                        sess_data.trialTypeMat[:6, :].T, sess_data.trialTypeMat[6, :].T,
                        sess_data.trialPropertiesHash.value[0] * trial_time_conversion,
                        sess_data.trialPropertiesHash.value[1] * trial_time_conversion,
                        sess_data.trialPropertiesHash.value[2] * trial_time_conversion,
                        sess_data.trialPropertiesHash.value[-1])

        print('---- Ingesting trial data ----')
        (session_trials, behavior_trials, trial_events, photostim_trials,
         photostim_events, photostim_traces, lick_traces) = [], [], [], [], [], [], []

        for (tr_id, tr_start, trial_type_mtx, is_early_lick,
             sample_start, delay_start, response_start, photostim_type) in tqdm(trial_zip):

            tkey = dict(session_key, trial=tr_id,
                        start_time=Decimal(tr_start),
                        stop_time=Decimal(tr_start + response_start + post_resp_tlim))
            session_trials.append(tkey)

            trial_type = np.array(trial_type_str)[trial_type_mtx.astype(bool)]
            if len(trial_type) == 1:
                outcome, trial_instruction = trial_type_mapper[trial_type[0]]
            else:
                outcome, trial_instruction = 'non-performing', 'non-performing'

            bkey = dict(tkey, **task_protocol,
                        trial_instruction=trial_instruction,
                        outcome=outcome,
                        early_lick='early' if is_early_lick else 'no early')
            behavior_trials.append(bkey)

            lick_traces.append(dict(bkey, lick_trace=lick_trace[ts_trial == tr_id],
                                    lick_trace_timestamps=ts_tvec[ts_trial == tr_id] - tr_start))

            for etype, etime in zip(('sample', 'delay', 'go'), (sample_start, delay_start, response_start)):
                if not np.isnan(etime):
                    trial_events.append(dict(tkey, trial_event_id=len(trial_events)+1,
                                             trial_event_type=etype, trial_event_time=etime))

            if photostims and photostim_type != 0:
                pkey = dict(tkey)
                photostim_trials.append(pkey)
                if photostim_type in (1, 2):
                    photostim_key = (photostims & {'stim_brain_area': photostim_mapper[photostim_type.astype(int)]})
                    if photostim_key:
                        photostim_key = photostim_key.fetch1('KEY')
                        stim_power = laser_power[ts_trial == tr_id]
                        stim_power = np.where(stim_power == np.Inf, 0, stim_power)  # handle cases where stim power is Inf
                        photostim_events.append(dict(pkey, **photostim_key, photostim_event_id=len(photostim_events)+1,
                                                     photostim_event_time=delay_start,  # this study has photostrim strictly in the delay period
                                                     duration=photostim_dur,
                                                     power=stim_power.max() if len(stim_power) > 0 else None))
                        photostim_traces.append(dict(pkey, aom_input_trace=aom_input_trace[ts_trial == tr_id],
                                                     laser_power=laser_power[ts_trial == tr_id],
                                                     photostim_timestamps=ts_tvec[ts_trial == tr_id] - tr_start))

        # insert trial info
        experiment.SessionTrial.insert(session_trials, **insert_kwargs)
        experiment.BehaviorTrial.insert(behavior_trials, **insert_kwargs)
        experiment.PhotostimTrial.insert(photostim_trials, **insert_kwargs)
        experiment.TrialEvent.insert(trial_events, **insert_kwargs)
        experiment.PhotostimEvent.insert(photostim_events, **insert_kwargs)
        experiment.PhotostimTrace.insert(photostim_traces, **insert_kwargs)
        tracking.LickTrace.insert(lick_traces, **insert_kwargs)

        # ---- units ----
        insert_key = (ephys.ProbeInsertion & session_key).fetch1()
        ap, dv = (ephys.ProbeInsertion.InsertionLocation & session_key).fetch1('ap_location', 'dv_location')
        e_sites = {e: (y - float(ap), z - float(dv)) for e, y, z in
                   zip(*(ephys.ProbeInsertion.ElectrodeSitePosition & session_key).fetch(
                       'electrode', 'electrode_posy', 'electrode_posz'))}
        tr_events = {tr: (float(stime), float(gotime)) for tr, stime, gotime in
                     zip(*(experiment.SessionTrial * experiment.TrialEvent
                           & session_key & 'trial_event_type = "go"').fetch('trial', 'start_time', 'trial_event_time'))}

        print('---- Ingesting spike data ----')
        unit_spikes, unit_cell_types, trial_spikes = [], [], []
        for u_name, u_value in tqdm(zip(sess_data.eventSeriesHash.keyNames, sess_data.eventSeriesHash.value)):
            unit = int(re.search('\d+', u_name).group())
            electrode = np.unique(u_value.channel)[0]
            spike_times = u_value.eventTimes * unit_time_converstion

            unit_key = dict(insert_key, clustering_method=clustering_method, unit=unit)
            unit_spikes.append(dict(unit_key, electrode_group=0, unit_quality='good',
                                    electrode=electrode, unit_posx=e_sites[electrode][0], unit_posy=e_sites[electrode][1],
                                    spike_times=spike_times, waveform=u_value.waveforms))
            unit_cell_types += [dict(unit_key, cell_type=(cell_type_mapper[cell_type] if len(cell_type) > 0 else 'N/A'))
                                for cell_type in (u_value.cellType
                                                  if isinstance(u_value.cellType, (list, np.ndarray))
                                                  else [u_value.cellType])]
            # get trial's spike times, shift by start-time, then by go-time -> align to go-time
            trial_spikes += [dict(unit_key, trial=tr, spike_times=(spike_times[u_value.eventTrials == tr]
                                                                   - tr_events[tr][0] - tr_events[tr][1]))
                             for tr in set(u_value.eventTrials) if tr in tr_events]

        ephys.Unit.insert(unit_spikes, **insert_kwargs)
        ephys.UnitCellType.insert(unit_cell_types, **insert_kwargs)
        ephys.TrialSpikes.insert(trial_spikes, **insert_kwargs)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
