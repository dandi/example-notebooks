import os
import re
import pathlib
import h5py as h5
import numpy as np
from decimal import Decimal
from tqdm import tqdm
import glob
import datajoint as dj
from collections.abc import Iterable

from pipeline import (reference, subject, acquisition, extracellular, behavior, stimulation, virus, utilities)

path = pathlib.Path(dj.config['custom'].get('data_directory')).as_posix()
fnames = np.hstack(glob.glob(os.path.join(dir_files[0], '*.nwb'))
                   if len(dir_files[1]) == 0 and dir_files[0].find('VPM_silicon_probe') != -1 else []
                   for dir_files in os.walk(path))

for fname in fnames:
    print(f'Reading {fname}...')
    nwb = h5.File(fname, 'r')
    subject_info = {c: nwb['general']['subject'][c].value.decode('UTF-8')
                    for c in ('description', 'sex', 'species', 'weight', 'age', 'genotype')}
    # force subject_id to be lower-case for consistency
    subject_info['subject_id'] = os.path.split(fname)[-1].split('_')[0].lower()

    # dob and sex
    subject_info['sex'] = subject_info['sex'][0].upper()
    dob_str = re.search('(?<=Date of birth:\s)(.*)', subject_info['description'])
    if utilities.parse_date(dob_str.group()) is not None:
        subject_info['date_of_birth'] = utilities.parse_date(dob_str.group())

    # allele
    allele_str = re.search('(?<=Animal Strain:\s)(.*)', subject_info['description']).group()  # extract the information related to animal allele
    allele_dict = {alias.lower(): allele for alias, allele in subject.AlleleAlias.fetch()}
    regex_str = '|'.join([re.escape(alias) for alias in allele_dict.keys()])
    alleles = [allele_dict[s.lower()] for s in re.findall(regex_str, allele_str, re.I)]
    # source
    source_str = re.search('(?<=Animal source:\s)(.*)', subject_info['description']).group()  # extract the information related to animal allele
    source_dict = {alias.lower(): source for alias, source in reference.AnimalSourceAlias.fetch()}
    regex_str = '|'.join([re.escape(alias) for alias in source_dict.keys()])
    subject_info['animal_source'] = source_dict[re.search(regex_str, source_str, re.I).group().lower()] if re.search(regex_str, source_str, re.I) else 'N/A'

    with subject.Subject.connection.transaction:
        if subject_info not in subject.Subject.proj():
            subject.Subject.insert1(subject_info, ignore_extra_fields = True)
            subject.Subject.Allele.insert((dict(subject_info, allele = k)
                                           for k in alleles), ignore_extra_fields = True)

    # ==================== session ====================
    # -- session_time
    sess_time = re.search('(?<=_)(\d{8})(?=\.nwb)', nwb['general']['session_id'].value.decode('UTF-8')).group()
    session_info = dict(subject_info,
                        session_id=os.path.split(fname)[-1].replace('.nwb', ''),
                        institution=nwb['general']['institution'].value.decode('UTF-8'),
                        related_publications=nwb['general']['related_publications'].value.decode('UTF-8'),
                        surgery=nwb['general']['surgery'].value.decode('UTF-8'),
                        lab=nwb['general']['lab'].value.decode('UTF-8'),
                        notes=nwb['general']['notes'].value.decode('UTF-8'),
                        identifier=nwb['identifier'].value.decode('UTF-8'),
                        session_note=nwb['session_description'].value.decode('UTF-8'),
                        session_time=utilities.parse_date(sess_time))

    experimenters = nwb['general']['experimenter'].value.decode('UTF-8')
    experiment_types = re.split('Experiment type: ', session_info['notes'])[-1]
    experiment_types = re.split(',\s?', experiment_types)

    # experimenter and experiment type (possible multiple experimenters or types)
    experimenters = [experimenters] if np.array(
        experimenters).size <= 1 else experimenters  # in case there's only 1 experimenter

    reference.Experimenter.insert(zip(experimenters), skip_duplicates = True)
    acquisition.ExperimentType.insert(zip(experiment_types), skip_duplicates=True)

    sess_key = {'subject_id': subject_info["subject_id"],
                'session_time': session_info["session_time"],
                'session_id': session_info['session_id']}

    with acquisition.Session.connection.transaction:
        if session_info not in acquisition.Session.proj():
            acquisition.Session.insert1(session_info, ignore_extra_fields=True)
            acquisition.Session.Experimenter.insert((dict(session_info, experimenter=k)
                                                     for k in experimenters), ignore_extra_fields=True)
            acquisition.Session.ExperimentType.insert((dict(session_info, experiment_type=k)
                                                       for k in experiment_types), ignore_extra_fields=True)
        print(f'\nCreating Session - Subject: {subject_info["subject_id"]} - Date: {session_info["session_time"]}')

    # ==================== Extracellular ====================
    # # Probe
    # probe_re_pattern = re.compile(r'(.*)probeSource: (?P<probe_source>.*)probeType: (?P<probe>.*)')
    # match = probe_re_pattern.match(nwb['general']['extracellular_ephys']['shank0']['description'].value.decode('UTF-8'))

    ec_probe = {'probe_name': '4x8_Neuronexus_Z50um_X200um',  #  hardcoded
                'channel_counts': len(nwb['general']['extracellular_ephys']['electrode_map']),
                'probe_source': 'NeuroNexus',
                'probe_desc': nwb['general']['devices']['ephys-acquisition'].value.decode('UTF-8')}
    with reference.Probe.connection.transaction:
        if ec_probe not in reference.Probe.proj():
            reference.Probe.insert1(ec_probe)
            reference.Probe.Shank.insert((
                dict(ec_probe, shank_id=int(re.search('\d+', shank.decode('UTF-8')).group()))
                for shank in set(nwb['general']['extracellular_ephys']['electrode_group'].value)),
            ignore_extra_fields=True)
            reference.Probe.Channel.insert((
                dict(ec_probe,
                     channel_id=chn_id + 1,  # channel starts from 1
                     shank_id=int(re.search('\d+', chn_shank.decode('UTF-8')).group()),
                     channel_x_pos=chn_loc[0],
                     channel_y_pos=chn_loc[1],
                     channel_z_pos=chn_loc[2])
                for chn_id, (chn_loc, chn_shank) in enumerate(
                zip(nwb['general']['extracellular_ephys']['electrode_map'],
                    nwb['general']['extracellular_ephys']['electrode_group']))),
                ignore_extra_fields=True)

    # Probe-insertion
    # For this study all extracellular probe recordings are at the VPM of the thalamus
    hemisphere = 'left'
    brain_location = {'brain_region': 'thalamus',
                      'brain_subregion': 'VPM',
                      'cortical_layer': 'N/A',
                      'hemisphere': hemisphere}
    reference.BrainLocation.insert1(brain_location, skip_duplicates=True)

    with extracellular.ProbeInsertion.connection.transaction:
        if {**ec_probe, **sess_key} not in extracellular.ProbeInsertion.proj():
            extracellular.ProbeInsertion.insert1({**ec_probe, **sess_key}, ignore_extra_fields=True)
            for shank_id in set(nwb['general']['extracellular_ephys']['electrode_group'].value):
                shank = nwb['general']['extracellular_ephys'][shank_id.decode('UTF-8')]
                shank_loc = re.findall('\d+\.\d+', shank['location'].value.decode('UTF-8'))
                action_location = dict(brain_location,
                                       coordinate_ref = 'bregma',
                                       coordinate_ap = round(Decimal(shank_loc[0]), 2),
                                       coordinate_ml = round(Decimal(shank_loc[1]), 2),
                                       coordinate_dv = Decimal('2.5'))  #  depth info from the paper
                reference.ActionLocation.insert1(action_location, skip_duplicates = True)
                extracellular.ProbeInsertion.InsertLocation.insert1(
                    dict({**ec_probe, **sess_key, **action_location},
                         shank_id=int(re.search('\d+', shank_id.decode('UTF-8')).group())),
                    ignore_extra_fields=True)

    # Unit spikes
    extracellular_units = nwb['processing']['extracellular_units']
    for u in extracellular_units['UnitTimes']['unit_list'].value:
        unit = u.decode('UTF-8')
        unit_id = int(re.search('\d+', unit).group())
        with extracellular.UnitSpikeTimes.connection.transaction:
            extracellular.UnitSpikeTimes.insert1(
                dict({**ec_probe, **sess_key},
                     unit_id=unit_id,
                     cell_desc=''.join([v.decode('UTF-8').replace(unit + ' - ', '')
                                        for v in extracellular_units['UnitTimes']['cell_types'].value
                                        if v.decode('UTF-8').find(unit) != -1]),
                     spike_times=extracellular_units['UnitTimes'][unit]['times'].value),
                ignore_extra_fields=True, skip_duplicates=True)
            extracellular.UnitSpikeTimes.UnitChannel.insert(
                (dict({**ec_probe, **sess_key}, unit_id=unit_id, channel_id=chn)
                 for chn in extracellular_units['EventWaveform'][unit]['electrode_idx'].value),
                ignore_extra_fields=True, skip_duplicates=True)
            extracellular.UnitSpikeTimes.SpikeWaveform.insert(
                (dict({**ec_probe, **sess_key}, unit_id = unit_id, channel_id = chn,
                      spike_waveform=waveform)
                 for chn, waveform in zip(extracellular_units['EventWaveform'][unit]['electrode_idx'].value,
                                          extracellular_units['EventWaveform'][unit]['data'].value.transpose((2,0,1)))),
                ignore_extra_fields=True, skip_duplicates=True)

    # ==================== Behavior ====================

    behavior.LickTrace.insert1(dict(
        sess_key,
        lick_trace=nwb['acquisition']['timeseries']['lick_trace']['data'].value,
        lick_trace_timestamps=nwb['acquisition']['timeseries']['lick_trace']['timestamps'].value),
        skip_duplicates=True, allow_direct_insert=True)

    whisker_timeseries = nwb['processing']['whisker']['BehavioralTimeSeries']

    whisker_configs = ([wk.decode('UTF-8') for wk in nwb["general"]["whisker_configuration"].value]
                       if nwb["general"]["whisker_configuration"].value.shape
                       else [wk for wk in nwb["general"]["whisker_configuration"].value.decode('UTF-8').split(',')])
    principal_whisker_idx = int(nwb['analysis']['principal_whisker'].value[0]
                                if isinstance(nwb['analysis']['principal_whisker'].value, Iterable)
                                else nwb['analysis']['principal_whisker'].value)
    principal_whisker, principal_whisker_num = whisker_configs[principal_whisker_idx-1], '1'

    print(f'Whiskers: {whisker_configs} - Principal: {principal_whisker}')
    for whisker_config, whisker_num in zip(whisker_configs,
                                           set([re.search('\d', k).group() for k in whisker_timeseries])):
        whisker_key = dict(sess_key, whisker_config=whisker_config)
        principal_whisker_num = whisker_num if whisker_config == principal_whisker else principal_whisker_num
        if whisker_key not in behavior.Whisker.proj():
            behavior.Whisker.insert1(dict(
                whisker_key,
                principal_whisker=(whisker_config == principal_whisker),
                pole_available=whisker_timeseries['block_mask_' + whisker_num]['data'].value.flatten(),
                touch_offset=whisker_timeseries['touch_offset_' + whisker_num]['data'].value.flatten(),
                touch_onset=whisker_timeseries['touch_onset_' + whisker_num]['data'].value.flatten(),
                whisker_angle=whisker_timeseries['whisker_angle_' + whisker_num + '_whisker']['data'].value.flatten(),
                whisker_curvature=whisker_timeseries['whisker_curvature_' + whisker_num + '_whisker']['data'].value.flatten(),
                behavior_timestamps=whisker_timeseries['touch_onset_' + whisker_num]['timestamps'].value),
                skip_duplicates=True, allow_direct_insert=True)
            print(f'Ingest whisker data: {whisker_config} - Principal: {whisker_config == principal_whisker}')

    # ==================== Trials ====================
    # -- read trial-related info -- nwb['epochs'], nwb['analysis'], nwb['stimulus']['presentation'])
    trials = dict(trial_names=[tr for tr in nwb['epochs']],
                  trial_type=[nwb['epochs'][v]['tags'].value[0].decode('UTF-8') for v in nwb['epochs']],
                  start_times=[v['start_time'].value for v in nwb['epochs'].values()],
                  stop_times=[v['stop_time'].value for v in nwb['epochs'].values()],
                  good_trials=[k.any() for k in nwb['analysis']['good_trials_units'].value],
                  trial_response=nwb['analysis']['trial_type_mat'].value.T,
                  pole_pos_time=nwb['stimulus']['presentation']['pole_position']['timestamps'].value,
                  pole_pos=nwb['stimulus']['presentation']['pole_position']['data'].value,
                  pole_in_times=nwb['stimulus']['presentation']['pole_in']['timestamps'].value,
                  pole_out_times=nwb['stimulus']['presentation']['pole_out']['timestamps'].value)

    lick_times = (nwb['acquisition']['timeseries']['lick_trace']['data'].value *
                  (nwb['acquisition']['timeseries']['lick_trace']['timestamps'].value))
    lick_times = lick_times[lick_times != 0]
    touch_times = (nwb['processing']['whisker']['BehavioralTimeSeries']['touch_onset_' + principal_whisker_num]['data'].value.flatten() *
                   nwb['processing']['whisker']['BehavioralTimeSeries']['touch_onset_' + principal_whisker_num]['timestamps'].value.flatten())
    touch_times = touch_times[touch_times != 0]  # convert ms -> s (behav data timestamps are in millisecond)

    # form new key-values pair and insert key
    trial_set = dict(sess_key, trial_counts=len(trials['trial_names']))
    if trial_set not in acquisition.TrialSet.proj():
        print(f'Ingest trial information\n')
        acquisition.TrialSet.insert1(trial_set, allow_direct_insert=True)
        for idx, trial_id in tqdm(enumerate(trials['trial_names'])):
            trial_key = dict(trial_set, trial_id=int(re.search('\d+', trial_id).group()))
            trial_detail = dict(start_time=trials['start_times'][idx],
                                stop_time=trials['stop_times'][idx],
                                trial_is_good=trials['good_trials'][idx],
                                trial_type='Go' if trials['trial_type'][idx] in ('Hit', 'Miss') else 'NoGo',
                                trial_stim_present=False,  # no photostim info found in data -> default to False
                                trial_response=trials['trial_type'][idx],
                                pole_position=trials['pole_pos'][idx])
            # insert
            acquisition.TrialSet.Trial.insert1({**trial_key, **trial_detail}, ignore_extra_fields=True, skip_duplicates=True, allow_direct_insert=True)
            # ======== Now add trial event timing to the EventTime part table ====
            # -- events timing
            trial_lick_times = lick_times[np.logical_and(lick_times > trial_detail['start_time'],
                                                   lick_times < trial_detail['stop_time'])]
            trial_touch_times = touch_times[np.logical_and(touch_times > trial_detail['start_time'],
                                                     touch_times < trial_detail['stop_time'])]
            events = dict(trial_start=0,
                          trial_stop=trial_detail['stop_time'] - trial_detail['start_time'],
                          pole_in=trials['pole_in_times'][idx] - trial_detail['start_time'],
                          pole_out=trials['pole_out_times'][idx] - trial_detail['start_time'],
                          pole_pos=trials['pole_pos_time'][idx] - trial_detail['start_time'],
                          first_lick=trial_lick_times[0] - trial_detail['start_time'] if trial_lick_times.size else np.nan,
                          first_touch=trial_touch_times[0] - trial_detail['start_time'] if trial_touch_times.size else np.nan)
            acquisition.TrialSet.EventTime.insert((dict(trial_key, trial_event=k, event_time = v)
                                                   for k, v in events.items()),
                                                  ignore_extra_fields=True, allow_direct_insert=True)


    # ==================== Photo stimulation ====================
    if 'optogenetics' in nwb['general']:
        for site in nwb['general']['optogenetics']:
            opto_descs = nwb['general']['optogenetics'][site]['description'].value.decode('UTF-8')
            opto_excitation_lambda = (re.search("\d+",
                                                nwb['general']['optogenetics'][site]['excitation_lambda']
                                                .value.decode('UTF-8')).group())
            splittedstr = re.split(',\s?coordinates:\s?',
                                   nwb['general']['optogenetics'][site]['location'].value.decode('UTF-8'))
            brain_region = splittedstr[0]
            coord_ap_ml_dv = re.findall('\d+\.\d+', splittedstr[-1])

            # -- BrainLocation
            brain_location = {'brain_region': brain_region,
                              'brain_subregion': 'N/A',
                              'cortical_layer': 'N/A',
                              'hemisphere': hemisphere}
            reference.BrainLocation.insert1(brain_location, skip_duplicates=True)
            # -- ActionLocation
            action_location = dict(brain_location,
                                   coordinate_ref = 'bregma',
                                   coordinate_ap = round(Decimal(coord_ap_ml_dv[0]), 2),
                                   coordinate_ml = round(Decimal(coord_ap_ml_dv[1]), 2),
                                   coordinate_dv = round(Decimal(coord_ap_ml_dv[2]), 2))
            reference.ActionLocation.insert1(action_location, skip_duplicates=True)

            # -- Device
            stim_device = nwb['general']['optogenetics'][site]['device'].value.decode('UTF-8')
            stimulation.PhotoStimDevice.insert1({'device_name': stim_device}, skip_duplicates=True)

            # -- PhotoStimulationProtocol
            photim_stim_protocol = dict(protocol=re.search('\d+', site).group(),
                                    device_name=stim_device,
                                    photo_stim_method='laser',
                                    photo_stim_excitation_lambda=float(opto_excitation_lambda),
                                    photo_stim_notes=(f'{site} - {opto_descs}'))
            stimulation.PhotoStimProtocol.insert1(photim_stim_protocol, skip_duplicates=True)

            # -- PhotoStimulation
            stim_presentation = None
            for f in nwb['stimulus']['presentation']:
                if ('site' in nwb['stimulus']['presentation'][f]
                        and nwb['stimulus']['presentation'][f]['site'].value.decode('UTF-8') == site):
                    stim_presentation = nwb['stimulus']['presentation'][f]
                    break

            if stim_presentation and dict({**subject_info, **session_info}, photostim_id=site) not in stimulation.PhotoStimulation.proj():
                photostim_data = stim_presentation['data'].value
                photostim_timestamps = stim_presentation['timestamps'].value
                stimulation.PhotoStimulation.insert1(dict({**session_info, **photim_stim_protocol, **action_location},
                                                          photostim_id=site,
                                                          photostim_timeseries=photostim_data,
                                                          photostim_timestamps=photostim_timestamps),
                                                     ignore_extra_fields = True)
                print(f'Ingest photostim: {site}')

    # ==================== Virus ====================
    virus_desc_pattern = re.compile(r'virusSource: (?P<virus_source>.*); virusID: (?P<virus_id>.*); virusLotNumber: (?P<virus_lot_num>.*); inflectionCoordinates: (?P<injection_coord>.*); infectionLocation: (?P<injection_loc>.*); virusTiter: (?P<virus_titer>.*); injectionVolume: (?P<injection_volume>.*); injectionDate: (?P<injection_date>.*);(.+)')
    match = virus_desc_pattern.match(nwb['general']['virus'].value.decode('UTF-8'))

    if match and match['virus_id']:
        virus_info = dict(
            virus_source=match['virus_source'],
            virus=match['virus_id'],
            virus_lot_number=match['virus_lot_num'],
            virus_titer=float(match['virus_titer']))

        virus.Virus.insert1(virus_info, skip_duplicates=True)

        brain_location = {'brain_region': match['injection_loc'],
                          'brain_subregion': match['injection_coord'].split(' ')[0],
                          'cortical_layer': 'N/A',
                          'hemisphere': hemisphere}
        reference.BrainLocation.insert1(brain_location, skip_duplicates=True)

        virus.VirusInjection.insert1(dict({**virus_info, **subject_info, **brain_location},
                                          coordinate_ref='bregma',
                                          injection_date=utilities.parse_date(
                                              re.search('(\d{4})-(\d{2})-(\d{2})', match['injection_date']).group()),
                                          injection_volume=round(Decimal(re.match('\d+', match['injection_volume']).group()), 2)),
                                     ignore_extra_fields=True, skip_duplicates=True)
        print('Ingest virus injection')
