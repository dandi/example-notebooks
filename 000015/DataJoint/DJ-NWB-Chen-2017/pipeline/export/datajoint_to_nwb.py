#!/usr/bin/env python3
import os, sys
import collections
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from datetime import datetime
from dateutil.tz import tzlocal
import pytz
import re
import numpy as np
import json
import pandas as pd

from pipeline import (lab, experiment, imaging, virus)
import pynwb
from pynwb import NWBFile, NWBHDF5IO

# ============================== SET CONSTANTS ==========================================
default_nwb_output_dir = os.path.join('/data', 'NWB 2.0')
zero_zero_time = datetime.strptime('00:00:00', '%H:%M:%S').time()  # no precise time available
institution = 'Janelia Research Campus'


def export_to_nwb(session_key, nwb_output_dir=default_nwb_output_dir, save=False, overwrite=False):

    this_session = (experiment.Session & session_key).fetch1()
    print(f'Exporting to NWB 2.0 for session: {this_session}...')
    # ===============================================================================
    # ============================== META INFORMATION ===============================
    # ===============================================================================

    # -- NWB file - a NWB2.0 file for each session
    file_name = '_'.join(
        [this_session['subject_nickname'],
         this_session['session_date'].strftime('%Y-%m-%d'),
         str(this_session['session'])])
    nwbfile = NWBFile(
        identifier=file_name,
        related_publications='http://dx.doi.org/10.1016/j.neuron.2017.05.005',
        experiment_description='Two-photon experiment recorded in {}'.format(this_session['brain_location_name']),
        session_description='Imaging session',
        session_start_time=datetime.combine(this_session['session_date'], zero_zero_time),
        file_create_date=datetime.now(tzlocal()),
        experimenter=this_session['username'],
        institution=institution,
        keywords=['motor planning', 'anterior lateral cortex', 'medial motor cortex',
                  'ALM', 'MM', 'Two-photon imaging'])

    # --- subject ---
    subj = (lab.Subject & session_key).fetch1()
    nwbfile.subject = pynwb.file.Subject(
        subject_id=this_session['subject_nickname'],
        genotype=' x '.join((lab.Subject.GeneModification
                             & subj).fetch('gene_modification')),
        sex=subj['sex'],
        species=subj['species'],
        date_of_birth=datetime.combine(subj['date_of_birth'], zero_zero_time) if subj['date_of_birth'] else None)
    # --- virus ---
    nwbfile.virus = json.dumps([{k: str(v) for k, v in virus_injection.items() if k not in subj}
                                for virus_injection in virus.VirusInjection * virus.Virus & session_key])

    # ===============================================================================
    # ======================== IMAGING & SEGMENTATION ===============================
    # ===============================================================================

    scan = (imaging.Scan & session_key).fetch1()

    # ---- Structural Images ----------
    images = pynwb.base.Images(name='images', description='Structural images of a scanning')

    if isinstance(scan['image_gcamp'], np.ndarray):
        gcamp = pynwb.image.GrayscaleImage('GCaMP at 940nm', scan['image_gcamp'])
        images.add_image(gcamp)
    if isinstance(scan['image_ctb'], np.ndarray):
        ctb = pynwb.image.RGBImage('CTB-647 IT', scan['image_ctb'])
        images.add_image(ctb)
    if isinstance(scan['image_beads'], np.ndarray):
        beads = pynwb.image.GrayscaleImage('Beads PT', scan['image_beads'])
        images.add_image(beads)

    nwbfile.add_acquisition(images)

    time_stamps = scan['frame_time']
    starting_time = time_stamps[0]
    rate = 1/np.median(np.diff(time_stamps))

    imaging_plane = nwbfile.create_imaging_plane(
        name='ImagingPlane',
        optical_channel=pynwb.ophys.OpticalChannel(
            name='green', description='green channel', emission_lambda=500.),
        description='Imaging session for PT and IT neurons during audio delay task',
        device=nwbfile.create_device(name='two-photon microscope with Thorlabs resonant galvo scannner'),
        excitation_lambda=940.,
        imaging_rate=rate,
        indicator='GCaMP6s',
        location='ALM',
        conversion=1e-6,
        unit='micrometers')

    # ----- Segementation information -----
    # link the imaging segmentation to the nwb file
    ophys = nwbfile.create_processing_module('ophys', 'Processing result of imaging')
    img_seg = pynwb.ophys.ImageSegmentation()
    ophys.add(img_seg)

    pln_seg = img_seg.create_plane_segmentation(
    name='PlaneSegmentation',
    description='output from segmenting the current imaging plane',
    imaging_plane=imaging_plane)

    roi_fluorescence = pynwb.ophys.Fluorescence()
    ophys.add(roi_fluorescence)

    # insert ROI mask
    rois = (imaging.Scan.Roi & this_session).fetch(as_dict=True)

    roi_indices, roi_traces, neuropil_traces = (imaging.Scan.Roi & this_session).fetch(
        'roi_idx', 'roi_trace', 'neuropil_trace')
    roi_traces = np.transpose(np.squeeze(np.array(roi_traces.tolist())))
    neuropil_traces = np.transpose(np.squeeze(np.array(neuropil_traces.tolist())))

    for k, v in dict(
            cell_type='PT, IT, or unknown',
            included='whether to include this roi into later analyses'
        ).items():

        pln_seg.add_column(name=k, description=v)

    for roi in rois:
        mask = np.zeros([512, 512])
        mask[np.unravel_index(roi['roi_pixel_list']-1, mask.shape, 'F')] = 1

        pln_seg.add_roi(
            image_mask=mask.astype(bool),
            cell_type='unknown' if roi['cell_type']=='N/A' else roi['cell_type'],
            included=bool(roi['inc']))

    roi_region = pln_seg.create_roi_table_region(
        name='rois',
        description='table region for rois in this segmentation',
        region=list(roi_indices-1))

    roi_fluorescence.create_roi_response_series(
        name='RoiResponseSeries',
        data=roi_traces,
        description='average fluorescence of roi',
        rois=roi_region,
        unit='a.u.',
        starting_time=starting_time, rate=rate)
    roi_fluorescence.create_roi_response_series(
        name='NeuropilResponseSeries',
        data=neuropil_traces,
        description='average fluorescence of the neuropil surrounding the roi',
        rois=roi_region,
        unit='a.u.',
        starting_time=starting_time, rate=rate)

    # ===============================================================================
    # =============================== BEHAVIOR TRIALS ===============================
    # ===============================================================================

    # =============== TrialSet ====================
    # NWB 'trial' (of type dynamic table) by default comes with three mandatory attributes: 'start_time' and 'stop_time'
    # Other trial-related information needs to be added in to the trial-table as additional columns (with column name
    # and column description)

    dj_trial = experiment.SessionTrial * experiment.BehaviorTrial
    skip_adding_columns = experiment.Session.primary_key + ['trial_uid', 'trial']

    if experiment.SessionTrial & session_key:
        # Get trial descriptors from TrialSet.Trial and TrialStimInfo
        trial_columns = [{'name': tag,
                          'description': re.sub('\s+:|\s+', ' ', re.search(
                            f'(?<={tag})(.*)', str(dj_trial.heading)).group()).strip()}
                         for tag in dj_trial.heading.names
                         if tag not in skip_adding_columns + ['start_time', 'stop_time']]

        # Add new table columns to nwb trial-table for trial-label
        for c in trial_columns:
            nwbfile.add_trial_column(**c)

        # Add entry to the trial-table
        for trial in (dj_trial & session_key).fetch(as_dict=True):
            trial['start_time'] = float(trial['start_time'])
            trial['stop_time'] = float(trial['stop_time']) if trial['stop_time'] else 5.0
            [trial.pop(k) for k in skip_adding_columns]
            trial['early_lick'] = True if trial['early_lick'] == 'early' else False
            nwbfile.add_trial(**trial)

    # ===============================================================================
    # =============================== BEHAVIOR TRIAL EVENTS ==========================
    # ===============================================================================

    behavior = nwbfile.create_processing_module(
        'behavior', 'Time of behavioral events in this session')
    behav_event = pynwb.behavior.BehavioralEvents(name='BehavioralEvents')
    behavior.add_data_interface(behav_event)

    for trial_event_type in \
            (experiment.TrialEventType & \
                experiment.TrialEvent & session_key).fetch('trial_event_type'):
        event_times, trial_starts = \
            (experiment.TrialEvent * experiment.SessionTrial
                & session_key & {'trial_event_type': trial_event_type}).fetch(
            'trial_event_time', 'start_time')

        if trial_event_type == 'sample':
            description = 'Time stamps of the beginning of the sampling period on each trial.'
        elif trial_event_type == 'delay':
            description = 'Time stamps of the beginning of the delay period on each trial.'
        elif trial_event_type == 'go':
            description = 'Time stamps of the go cue signal on each trial.'

        if len(event_times) > 0:
            event_times = np.hstack(event_times.astype(float) + trial_starts.astype(float))
            behav_event.create_timeseries(
                name=trial_event_type, unit='a.u.', conversion=1.0,
                data=np.full_like(event_times, 1),
                timestamps=event_times,
                description=description)

    # =============== Write NWB 2.0 file ===============
    if save:
        save_file_name = ''.join([nwbfile.identifier, '.nwb'])
        if not os.path.exists(nwb_output_dir):
            os.makedirs(nwb_output_dir)
        if not overwrite and os.path.exists(os.path.join(nwb_output_dir, save_file_name)):
            return nwbfile
        with NWBHDF5IO(os.path.join(nwb_output_dir, save_file_name), mode = 'w') as io:
            io.write(nwbfile)
            print(f'Write NWB 2.0 file: {save_file_name}')

    return nwbfile

# ============================== EXPORT ALL ==========================================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        nwb_outdir = sys.argv[1]
    else:
        nwb_outdir = default_nwb_output_dir

    for skey in experiment.Session.fetch('KEY'):
        export_to_nwb(skey, nwb_output_dir=nwb_outdir, save=True, overwrite=True)
