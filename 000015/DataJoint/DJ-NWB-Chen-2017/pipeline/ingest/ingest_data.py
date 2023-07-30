import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import re
import scipy.io as sio
from tqdm import tqdm
import pathlib
from decimal import Decimal
import numpy as np
import h5py

from pipeline import lab, experiment, imaging
from pipeline import parse_date, time_unit_conversion_factor
from pipeline.ingest import ingest_lookup



def main(data_dir='/data'):
    data_dir = pathlib.Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f'Path not found!! {data_dir.as_posix()}')

    # ==================== DEFINE CONSTANTS =====================
    trial_type_mapper = {'CorrR': ('hit', 'right', 'no early'),
                         'CorrL': ('hit', 'left', 'no early'),
                         'ErrR': ('miss', 'right', 'no early'),
                         'ErrL': ('miss', 'left', 'no early'),
                         'NoLickR': ('ignore', 'right', 'no early'),
                         'NoLickL': ('ignore', 'left', 'no early'),
                         'LickEarly': ('non-performing', 'non-performing', 'early')
                        }

    cell_type_mapper = {'PT': 'PT', 'IT': 'IT', 'unidentified': 'N/A', 'in': 'interneuron', 'pn': 'Pyr'}

    task_protocol = {'task': 'audio delay', 'task_protocol': 1}


    kargs = dict(skip_duplicates=True,
                 ignore_extra_fields=True,
                 allow_direct_insert=True)

    # ================== INGESTION OF DATA ==================
    data_files = data_dir.glob('*.nwb')

    for data_file in data_files:
        print(f'-- Read {data_file} --')

        fname = data_file.stem + '.nwb'
        nwb = h5py.File(os.path.join('/data', fname), 'r')

        experimenter = nwb['general/experimenter'][()]
        lab.Person.insert1((experimenter, experimenter), **kargs)

        # ----------- meta-data -----------
        search_result = re.search(
            'nwb_(an\d+)_(\d+)_(.*)_(\d+)um.nwb', fname)
        subject_nickname = search_result.group(1)
        session_date = parse_date(search_result.group(2)).date()
        brain_location = 'left_' + search_result.group(3).lower()
        depth = int(search_result.group(4))

        subject = dict(subject_nickname=subject_nickname,
                       username=experimenter,
                       sex='M', species='Mus musculus',
                       animal_source='Jackson Labs') # inferred from paper

        modified_gene = dict(
            gene_modification='Thy1-GCaMP6s',
            gene_modification_description='GP4.3')

        lab.ModifiedGene.insert1(modified_gene, **kargs)
        lab.Subject.insert1(subject, skip_duplicates=True)
        session_date = parse_date(
            re.search(f'nwb_{subject_nickname}_(\d+)_', fname).group(1))

        if len(experiment.Session & subject):
            session = (lab.Subject & subject).aggr(
                experiment.Session.proj(session_user='username'),
                session_max='max(session)').fetch1('session_max') + 1
        else:
            session = 1

        current_session = dict(
            **subject, session_date=session_date,
            brain_location_name=brain_location,
            session=session)

        if imaging.TrialTrace & current_session:
            print('Data ingested, skipping over...')
            continue

        experiment.Session.insert1(current_session, **kargs)
        experiment.Session.ImagingDepth.insert1(
            dict(**current_session, imaging_depth=depth), **kargs)

        # ---- trial data ----

        print('---- Ingesting trial data ----')
        (session_trials, behavioral_trials, trial_events) = [], [], []

        pole_in = nwb['stimulus/presentation/pole_in/timestamps'][()]
        pole_out = nwb['stimulus/presentation/pole_out/timestamps'][()]
        auditory_cue = nwb['stimulus/presentation/auditory_cue/timestamps'][()]

        for i_trial in range(len(nwb['epochs'])):
            trial_num = i_trial + 1
            trial_path = 'epochs/trial_{0:03}/'.format(trial_num)
            tkey = dict(**current_session, trial=trial_num)

            trial_start = nwb[trial_path + 'start_time'][()]
            trial_stop = nwb[trial_path + 'stop_time'][()]
            sample_start = pole_in[i_trial] - trial_start
            delay_start = pole_out[i_trial] - trial_start
            response_start = auditory_cue[i_trial] - trial_start

            session_trials.append(
                dict(**tkey, start_time=Decimal(trial_start),
                    stop_time=Decimal(trial_stop)))

            outcome, trial_instruction, early = trial_type_mapper[nwb[trial_path + 'tags'][()][0]]
            behavioral_trials.append(
                dict(**tkey, **task_protocol,
                    trial_instruction=trial_instruction,
                    outcome=outcome,
                    early_lick=early))

            for etype, etime in zip(('sample', 'delay', 'go'), (sample_start, delay_start, response_start)):
                if not np.isnan(etime):
                    trial_events.append(
                        dict(**tkey, trial_event_id=len(trial_events)+1,
                            trial_event_type=etype, trial_event_time=etime))
        # insert trial info
        experiment.SessionTrial.insert(session_trials, **kargs)
        experiment.BehaviorTrial.insert(behavioral_trials, **kargs)
        experiment.TrialEvent.insert(trial_events, **kargs)

        # ---- Scan info ----

        print('---- Ingesting imaging data ----')

        imaging.Scan.insert1(
            dict(**current_session,
                image_gcamp=nwb['acquisition/images/green'][()],
                frame_time=nwb['processing/ROIs/ROI_001/timestamps'][()]),
            **kargs)

        tr_events = {tr: (float(stime), float(gotime)) for tr, stime, gotime in
                     zip(*(experiment.SessionTrial * experiment.TrialEvent
                           & current_session & 'trial_event_type = "go"').fetch(
                         'trial', 'start_time', 'trial_event_time'))}

        rois, trial_traces = [], []
        frame_time = nwb['processing/ROIs/ROI_001/timestamps'][()]
        for i_roi in range(len(nwb['processing/ROIs'])):
            roi_idx = i_roi + 1
            roi_path = 'processing/ROIs/ROI_{0:03}/'.format(roi_idx)
            roi_trace = nwb[roi_path + 'fmean'][()]
            neuropil_trace = nwb[roi_path + 'fmean_neuropil'][()]
            roi_trace_corrected = roi_trace - 0.7*neuropil_trace

            rois.append(
                dict(**current_session,
                     roi_idx=roi_idx,
                     roi_trace=roi_trace,
                     neuropil_trace=neuropil_trace,
                     roi_trace_corrected=roi_trace_corrected,
                     cell_type=cell_type_mapper[nwb[roi_path + 'cell_type'][()][0]],
                     ap_position=nwb[roi_path + 'AP_position_from_bregma_in_micron'][()][0],
                     ml_position=nwb[roi_path + 'ML_position_from_bregma_in_micron'][()][0],
                     roi_pixel_list=nwb[roi_path + 'pixel_list'][()],
                     inc=bool(np.mean(roi_trace)/np.mean(neuropil_trace)>1.05)))

            for tr in tr_events.keys():
                if tr in tr_events:
                    go_cue_time = sum(tr_events[tr])
                    go_id = np.abs(frame_time-go_cue_time).argmin()
                    idx = slice(go_id-70, go_id+45, 1)
                    baseline = np.mean(roi_trace_corrected[go_id-70:go_id-64])
                    trial_traces += [
                        dict(**current_session, roi_idx=roi_idx, trial=tr,
                             original_time=frame_time[idx],
                             aligned_time=frame_time[idx]-go_cue_time,
                             aligned_trace=roi_trace[idx],
                             aligned_trace_corrected=roi_trace_corrected[idx],
                             dff=(roi_trace_corrected[idx] - baseline)/baseline)]

        imaging.Scan.Roi.insert(rois, **kargs)
        imaging.TrialTrace.insert(trial_traces, **kargs)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()

    imaging.RoiAnalyses.populate(suppress_errors=True, display_progress=True)
