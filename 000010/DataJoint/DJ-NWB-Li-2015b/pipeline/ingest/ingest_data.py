import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import re
import scipy.io as sio
from tqdm import tqdm
import pathlib
from decimal import Decimal
import numpy as np

from pipeline import lab, experiment, imaging
from pipeline import parse_date, time_unit_conversion_factor


def main(data_dir='/data/data_structure'):
    data_dir = pathlib.Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f'Path not found!! {data_dir.as_posix()}')

    # ==================== DEFINE CONSTANTS =====================

    trial_type_str = ['HitL', 'HitR', 'ErrL', 'ErrR', 'NoLickL', 'NoLickR']
    trial_type_mapper = {'HitR': ('hit', 'right'),
                         'HitL': ('hit', 'left'),
                         'ErrR': ('miss', 'right'),
                         'ErrL': ('miss', 'left'),
                         'NoLickR': ('ignore', 'right'),
                         'NoLickL': ('ignore', 'left')}

    cell_type_mapper = {'p': 'PT', 'i': 'IT', '': 'N/A', 'in': 'interneuron', 'pn': 'Pyr'}

    post_resp_tlim = 2  # a trial may last at most 2 seconds after response cue

    task_protocol = {'task': 'audio delay', 'task_protocol': 1}


    insert_kwargs = {'ignore_extra_fields': True, 'allow_direct_insert': True, 'skip_duplicates': True}

    # ================== INGESTION OF DATA ==================
    data_files = data_dir.glob('*.mat')

    for data_file in data_files:
        print(f'-- Read {data_file} --')

        fname = data_file.stem
        subject_nickname = re.search('data_(an\d+)_', fname).group(1)
        session_date = parse_date(re.search(subject_nickname + '_(\d+_\d+_\d+_)', fname).group(1).replace('_', ''))
        depth = int(re.search('_(\d+)(_fv|$)', fname).group(1))
        fov = int(re.search('fv(\d+)', fname).group(1)) if re.search('fv(\d+)', fname) else 1

        sessions = (experiment.Session &
                    (lab.Subject & {'subject_nickname': subject_nickname}).proj() &
                    {'session_date': session_date, 'fov': fov} &
                    (experiment.Session.ImagingDepth & {'imaging_depth': depth}))
        if len(sessions) < 2:
            session_key = sessions.fetch1('KEY')
        else:
            raise Exception('Multiple sessions found for {fname}')

        print(f'\tMatched: {session_key}')

        if imaging.TrialTrace & session_key:
            print('Data ingested, skipping over...')
            continue

        sess_data = sio.loadmat(data_file, struct_as_record = False, squeeze_me=True)['obj']

        # ---- trial data ----
        trial_zip = zip(sess_data.trialIds, sess_data.trialStartTimes,
                sess_data.trialTypeMat[:6, :].T,
                sess_data.trialPropertiesHash.value[0],
                sess_data.trialPropertiesHash.value[1],
                sess_data.trialPropertiesHash.value[2])

        print('---- Ingesting trial data ----')
        (session_trials, behavior_trials, trial_events) = [], [], []

        for (tr_id, tr_start, trial_type_mtx,
            sample_start, delay_start, response_start) in tqdm(trial_zip):

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
                        early_lick='no early')
            behavior_trials.append(bkey)

            for etype, etime in zip(('sample', 'delay', 'go'), (sample_start, delay_start, response_start)):
                if not np.isnan(etime):
                    trial_events.append(dict(tkey, trial_event_id=len(trial_events)+1,
                                            trial_event_type=etype, trial_event_time=etime))

        # insert trial info
        experiment.SessionTrial.insert(session_trials, **insert_kwargs)
        experiment.BehaviorTrial.insert(behavior_trials, **insert_kwargs)
        experiment.TrialEvent.insert(trial_events, **insert_kwargs)

        # ---- Scan info ----

        scan = dict(**session_key,
            image_gcamp=sess_data.images.value[0],
            image_ctb=sess_data.images.value[1],
            image_beads=sess_data.images.value[2] if len(sess_data.images.value[2]) else np.nan,
            frame_time=sess_data.timeSeriesArrayHash.value[0].time)

        cell_type_vec = [ct if len(ct) else '' for ct in sess_data.timeSeriesArrayHash.value[0].cellType]

        rois = [dict(**scan, roi_idx=idx,
                cell_type=cell_type_mapper[cell_type],
                roi_trace=roi_trace,
                neuropil_trace=neuropil_trace,
                roi_pixel_list=roi_plist,
                neuropil_pixel_list=neuropil_plist,
                inc=bool(np.mean(roi_trace)/np.mean(neuropil_trace)>1.05))
                for (idx, cell_type, roi_trace, neuropil_trace, roi_plist, neuropil_plist) in
                    zip(sess_data.timeSeriesArrayHash.value[0].ids, cell_type_vec,
                        sess_data.timeSeriesArrayHash.value[0].valueMatrix,
                        sess_data.timeSeriesArrayHash.value[1].valueMatrix,
                        sess_data.timeSeriesArrayHash.value[0].pixel_list,
                        sess_data.timeSeriesArrayHash.value[1].pixel_list)]

        imaging.Scan.insert1(scan, **insert_kwargs)
        imaging.Scan.Roi.insert(rois, **insert_kwargs)

        tr_events = {tr: (float(stime), float(gotime)) for tr, stime, gotime in
                     zip(*(experiment.SessionTrial * experiment.TrialEvent
                           & session_key & 'trial_event_type = "go"').fetch('trial', 'start_time', 'trial_event_time'))}

        print('---- Ingesting trial trace ----')
        trials = sess_data.timeSeriesArrayHash.value[0].trial
        frame_time = sess_data.timeSeriesArrayHash.value[0].time

        trial_traces = []
        for roi_id, trace in tqdm(zip(sess_data.timeSeriesArrayHash.value[0].ids,
                                    sess_data.timeSeriesArrayHash.value[0].valueMatrix)):
            for tr in set(trials):
                if tr in tr_events:
                    go_cue_time = sum(tr_events[tr])
                    go_id = np.abs(frame_time-go_cue_time).argmin()
                    trial_traces += [dict(**scan, roi_idx=roi_id, trial=tr,
                                          original_time=frame_time[go_id-45:go_id+45],
                                          aligned_time=frame_time[go_id-45:go_id+45]-go_cue_time,
                                          aligned_trace=trace[go_id-45:go_id+45],
                                          dff=(trace[go_id-45:go_id+45] - np.mean(trace[go_id-45:go_id-39]))/np.mean(trace[go_id-45:go_id-39]))]

        imaging.TrialTrace.insert(trial_traces, **insert_kwargs)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
