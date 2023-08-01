import os
import numpy as np
from decimal import Decimal
import scipy.io as sio
import pandas as pd
from tqdm import tqdm
import glob
import datajoint as dj
from collections import Iterable
import pathlib

from pipeline import (reference, subject, acquisition,
                      extracellular, behavior, utilities)

# ================== Setup ==================
hemi_dict = {'L': 'left', 'R': 'right', 'B': 'bilateral'}
trial_type_and_response_dict = {0: ('lick right', 'correct'),
                                1: ('lick left', 'correct'),
                                2: ('lick right', 'incorrect'),
                                3: ('lick left', 'incorrect'),
                                4: ('lick right', 'no response'),
                                5: ('lick left', 'no response')}
# ================== Dataset ==================
path = pathlib.Path(dj.config['custom'].get('data_directory')).as_posix()

cell_type_tag = pd.read_excel(os.path.join(path, 'Animal Key.xlsx'),
                              index_col=0, usecols='A, B').to_dict().pop('Cell type tagged')

fnames = glob.glob(os.path.join(path, '*.mat'))
for fname in fnames:
    mat = sio.loadmat(fname, struct_as_record = False, squeeze_me = True)
    for sess_idx, (sess_meta, sess_obj, sess_tt, sess_psth) in tqdm(
            enumerate(zip(mat['meta'], mat['obj'], mat['tt'], mat['psth']))):

        subject_id, session_time = sess_meta.filename.replace('.mat', '').split('_')[-2:]

        # --- Subject - No info on: animal sex, dob, source, strains
        subject_info = dict(subject_id=subject_id.lower(),
                            species='Mus musculus',  # not available, hard-coded here
                            animal_source='N/A')  # animal source not available from data, nor 'sex'
        subject.Subject.insert1(subject_info, skip_duplicates=True)

        # --- Session - no session types
        session_info = dict(subject_id=subject_info['subject_id'],
                            session_id=sess_idx,
                            session_time=utilities.parse_date(session_time))

        experimenters = ['Mike Economo']  # hard-coded here

        with acquisition.Session.connection.transaction:
            if session_info not in acquisition.Session.proj():
                acquisition.Session.insert1(session_info, ignore_extra_fields=True)
                acquisition.Session.Experimenter.insert((dict(session_info, experimenter=k)
                                                         for k in experimenters), ignore_extra_fields=True)
            print(f'\nCreating Session - Subject: {subject_info["subject_id"]} - Date: {session_info["session_time"]}')

        # --- Probe ---
        probe = {'probe_name': sess_obj.sessionMeta.probeName,
                 'channel_counts': sum(g.size for g in sess_obj.sessionMeta.siteGroups)}
        with reference.Probe.connection.transaction:
            if probe not in reference.Probe.proj():
                reference.Probe.insert1(dict(probe, probe_type=sess_obj.sessionMeta.probeType))
                reference.Probe.Shank.insert(dict(probe, shank_id=int(shank.replace('shank', '')))
                                             for shank in sess_obj.sessionMeta.siteLabels)
                for chns, shank in zip(sess_obj.sessionMeta.siteGroups, sess_obj.sessionMeta.siteLabels):
                    reference.Probe.Channel.insert(dict(probe, channel_id=chn,
                                                        shank_id=int(shank.replace('shank', '')))
                                               for chn in chns)

        # --- ProbeInsertion ---
        # brain location
        brain_region, hemisphere = sess_obj.sessionMeta.location.split('_')
        brain_location = {'brain_region': brain_region,
                          'brain_subregion': 'N/A',
                          'cortical_layer': '5',  # layer 5, hard-coded info from the paper
                          'hemisphere': hemi_dict[hemisphere]}
        reference.BrainLocation.insert1(brain_location, skip_duplicates = True)

        probe_insert = {**session_info, **probe, **brain_location,
                        'insertion_depth': Decimal(sess_obj.sessionMeta.depth)}
        extracellular.ProbeInsertion.insert1(probe_insert, skip_duplicates=True)

        # --- TrialSet ---
        trial_time_convert = utilities.time_unit_conversion_factor[sess_obj.timeUnitNames[
            sess_obj.trialTimeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing

        trial_key = dict(session_info, trial_counts=len(sess_obj.trialIDs))
        with acquisition.TrialSet.connection.transaction:
            if trial_key not in acquisition.TrialSet.proj():
                acquisition.TrialSet.insert1(trial_key)

                trial_properties = sess_obj.trialPropertiesHash.value
                for trial_idx, (trial_id, trial_start, trial_type, good_trial, pole_in, pole_out,
                                cue_start) in enumerate(
                    zip(sess_obj.trialIDs, sess_obj.trialStartTimes * trial_time_convert, sess_obj.trialTypeMat.T,
                        trial_properties[3], trial_properties[0] * trial_time_convert,
                        trial_properties[1] * trial_time_convert, trial_properties[2] * trial_time_convert)):

                    trial_key['trial_id'] = trial_idx + 1  # trial-number starts from 1
                    trial_key['start_time'] = trial_start
                    trial_key['trial_stim_present'] = trial_type[-1]
                    trial_key['trial_is_good'] = good_trial

                    if trial_type[6]:
                        trial_key['trial_type'] = 'lick left' if trial_type[1] or trial_type[3] else 'lick right'
                        trial_key['trial_response'] = 'early lick'
                    else:
                        trial_key['trial_type'], trial_key['trial_response'] = trial_type_and_response_dict[
                            np.where(trial_type[:6])[0][0]]

                    acquisition.TrialSet.Trial.insert1(trial_key, ignore_extra_fields=True, skip_duplicates=True)

                    # ======== Now add trial event timing to the EventTime part table ====
                    events_time = dict(pole_in=pole_in, pole_out=pole_out, cue_start=cue_start)
                    # -- events timing
                    acquisition.TrialSet.EventTime.insert((dict(trial_key, trial_event=k, event_time=e)
                                                           for k, e in events_time.items()),
                                                          ignore_extra_fields=True, skip_duplicates=True)

        # --- Extracellular ---
        if sess_meta.unitNumber < 2:
            sess_meta.unitNum = sess_meta.unitNum,
            sess_obj.eventSeriesHash.value = sess_obj.eventSeriesHash.value,
            sess_meta.depth = sess_meta.depth,
            sess_meta.channel = sess_meta.channel,

        unit_cell_type = cell_type_tag[os.path.split(fname)[-1].replace('.mat', '')]
        trial_cue = sess_obj.trialPropertiesHash.value[2] * trial_time_convert  # cue onset relative to the start of the behavior system
        trial_start = sess_obj.trialStartTimes * trial_time_convert

        # cuetm: time of cue-onset with respect to the start of the ephys-recording system
        cuetm = np.full_like(sess_obj.sessionMeta.bitcode, -1).astype(float)
        cuetm[:len(sess_obj.sessionMeta.cuetm)] = sess_obj.sessionMeta.cuetm
        cuetm = cuetm[sess_obj.sessionMeta.bitcode > 0]

        starttm = sess_obj.sessionMeta.trialStartTm[sess_obj.sessionMeta.bitcode > 0]
        t_offset = cuetm - trial_cue + starttm + trial_start

        def extract_unit_data():
            for unit_id, unit_val, unit_depth, unit_chn in zip(
                    sess_meta.unitNum, sess_obj.eventSeriesHash.value,
                    sess_meta.depth, sess_meta.channel):
                unit_time_convert = utilities.time_unit_conversion_factor[sess_obj.timeUnitNames[unit_val.timeUnit - 1]]  # (-1) to take into account Matlab's 1-based indexing
                cell_type = 'unidentified' if unit_id <= 1000 else unit_cell_type if unit_id <= 2000 else 'L6 corticothalamic'
                # -- reconstruct session-long spike times from trial-based cue-aligned spike times
                # (obj.eventSeriesHash.value are spike times relative to go-cue)
                if not isinstance(unit_val.eventTrials, Iterable):
                    print(unit_val.eventTrials)
                    unit_val.eventTrials = np.array([unit_val.eventTrials])
                trial_based_timeshift = np.array([trial_start[tr] + trial_cue[tr] for tr in unit_val.eventTrials - 1])
                unit_sess_spike_times = unit_val.eventTimes * unit_time_convert + trial_based_timeshift
                yield (unit_id, unit_depth, cell_type,
                       unit_chn, str(unit_val.quality), unit_sess_spike_times)

        if not (extracellular.UnitSpikeTimes & probe_insert):
            extracellular.UnitSpikeTimes.insert(
                (dict(probe_insert, unit_id=unit_id, channel_id=chn, unit_cell_type=unit_cell_type,
                      unit_quality=quality, unit_depth=unit_depth, spike_times=spike_times)
                 for unit_id, unit_depth, unit_cell_type, chn, quality, spike_times in extract_unit_data()), skip_duplicates=True)

        # --- Behavior ---
        # reconstruct session-long lick times from trial-aligned lick times
        if not (behavior.LickTimes & session_info):
            left_licks = np.hstack(licks * trial_time_convert + trial_start[l_idx]
                                        for l_idx, licks in enumerate(sess_obj.trialPropertiesHash.value[5]))
            right_licks = np.hstack(licks * trial_time_convert + trial_start[l_idx]
                                        for l_idx, licks in enumerate(sess_obj.trialPropertiesHash.value[6]))

            behavior.LickTimes.insert1(dict(session_info, lick_left_times=left_licks, lick_right_times=right_licks),
                                       skip_duplicates=True)

        # --- Cue-start aligned spike times
        extracellular.TrialSegmentedUnitSpikeTimes.populate(probe_insert)

        # --- PSTH - the PSTH are actually already computed and now needed to be imported into DJ pipeline
        # Pre-computed PSTH are time-locked to cue-start (-3.3975s to 2.9975s)
        if sess_psth.ndim < 3:
            sess_psth = sess_psth.reshape((sess_psth.shape[0], 1, sess_psth.shape[1]))
        for unit_idx, psths in enumerate(sess_psth.transpose((1, 2, 0))):
            extracellular.PSTH.insert((dict(
                probe_insert,
                unit_id=sess_meta.unitNum[unit_idx],
                trial_id=trial_idx+1, trial_seg_setting=0,
                psth=psth, psth_time=mat['time']) for trial_idx, psth in enumerate(psths)),
                skip_duplicates=True, allow_direct_insert=True)
