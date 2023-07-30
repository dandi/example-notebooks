import os
from datetime import datetime

import numpy as np
import scipy.io as sio
import re
from decimal import Decimal
import pathlib

import datajoint as dj
from pipeline import (reference, subject, acquisition, stimulation, analysis, virus,
                      intracellular, behavior, utilities)


# ================== Dataset ==================
data_dir = pathlib.Path(dj.config['custom'].get('data_directory')).as_posix()
meta_data_dir = os.path.join(data_dir, 'metadata')
sess_data_dir = os.path.join(data_dir, 'datafiles')

# ===================== Part 1: meta_data ========
meta_data_files = os.listdir(meta_data_dir)
for meta_data_file in meta_data_files:
    print(f'-- Read {meta_data_file} --')
    meta_data = sio.loadmat(os.path.join(
        meta_data_dir, meta_data_file), struct_as_record=False, squeeze_me=True)['meta_data']

    # ==================== subject ====================
    subject_info = dict(subject_id=meta_data.animal_ID.lower(),
                        sex=meta_data.sex[0].upper() if meta_data.sex.size != 0 else 'U',
                        species=meta_data.species.lower())
    if meta_data.animal_background.size != 0:
        subject_info['subject_description'] = meta_data.animal_background
    # dob
    if meta_data.data_of_birth.size != 0:
        subject_info['date_of_birth'] = utilities.parse_date(meta_data.data_of_birth)

    # allele
    source_strain = meta_data.source_strain  # subject.Allele
    if len(source_strain) > 0:  # if found, search found string to find matched strain in db
        allele_dict = {alias.lower(): allele for alias, allele in subject.AlleleAlias.fetch()}
        regex_str = '|'.join([re.escape(alias) for alias in allele_dict.keys()])
        alleles = [allele_dict[s.lower()] for s in re.findall(regex_str, source_strain, re.I)]
    else:
        alleles = ['N/A']

    # source
    source_identifier = meta_data.source_identifier  # reference.AnimalSource
    if len(source_identifier) > 0:  # if found, search found string to find matched strain in db
        source_dict = {alias.lower(): source for alias, source in reference.AnimalSourceAlias.fetch()}
        regex_str = '|'.join([re.escape(alias) for alias in source_dict.keys()])
        subject_info['animal_source'] = (source_dict[
            re.search(regex_str, source_identifier, re.I).group().lower()]
                                         if re.search(regex_str, source_identifier, re.I) else 'N/A')
    else:
        subject_info['animal_source'] = 'N/A'

    with subject.Subject.connection.transaction:
        if subject_info not in subject.Subject.proj():
            subject.Subject.insert1(subject_info, ignore_extra_fields=True)
            subject.Subject.Allele.insert((dict(subject_info, allele = k)
                                           for k in alleles), ignore_extra_fields = True)

    # ==================== session ====================
    # -- session_time
    date_of_experiment = utilities.parse_date(str(meta_data.date_of_experiment))  # acquisition.Session
    if date_of_experiment is not None:
        session_info = {'session_id': re.search('Cell\d+', meta_data_file).group(),
                       'session_time': date_of_experiment}
        # experimenter and experiment type (possible multiple experimenters or types)
        experiment_types = meta_data.experiment_type
        experimenters = meta_data.experimenters  # reference.Experimenter
        experimenters = [experimenters] if np.array(experimenters).size <= 1 else experimenters  # in case there's only 1 experimenter

        reference.Experimenter.insert(zip(experimenters), skip_duplicates=True)
        acquisition.ExperimentType.insert(zip(experiment_types), skip_duplicates=True)

        with acquisition.Session.connection.transaction:
            if {**subject_info, **session_info} not in acquisition.Session.proj():
                acquisition.Session.insert1({**subject_info, **session_info}, ignore_extra_fields=True)
                acquisition.Session.Experimenter.insert((dict({**subject_info, **session_info}, experimenter=k) for k in experimenters), ignore_extra_fields=True)
                acquisition.Session.ExperimentType.insert((dict({**subject_info, **session_info}, experiment_type=k) for k in experiment_types), ignore_extra_fields=True)
            print(f'Creating Session - Subject: {subject_info["subject_id"]} - Date: {session_info["session_time"]}')

    # ==================== Intracellular ====================
    if isinstance(meta_data.extracellular, sio.matlab.mio5_params.mat_struct):
        extracellular = meta_data.extracellular
        brain_region = re.split(',\s?|\s', extracellular.atlas_location)[1]
        recording_coord_depth = extracellular.recording_coord_location[1]  # acquisition.RecordingLocation
        cortical_layer, brain_subregion = re.split(',\s?|\s', extracellular.recording_coord_location[0])[1:3]
        hemisphere = 'left'  # hardcoded here, not found in data, not found in paper
        brain_location = {'brain_region': brain_region,
                          'brain_subregion': brain_subregion,
                          'cortical_layer': cortical_layer,
                          'hemisphere': hemisphere,
                          'brain_location_full_name': extracellular.atlas_location}
        # -- BrainLocation
        if brain_location not in reference.BrainLocation.proj():
            reference.BrainLocation.insert1(brain_location)
        # -- Whole Cell Device
        ie_device = extracellular.probe_type.split(', ')[0]
        reference.WholeCellDevice.insert1({'device_name': ie_device, 'device_desc': extracellular.probe_type},
                                          skip_duplicates=True)
        # -- Cell
        cell_id = meta_data.cell.upper()
        cell_key = dict({**subject_info, **session_info, **brain_location},
                        cell_id=cell_id,
                        cell_type=extracellular.cell_type,
                        device_name=ie_device,
                        recording_depth=round(Decimal(re.match(
                            '\d+', extracellular.recording_coord_location[1]).group()), 2))
        if cell_key not in intracellular.Cell.proj():
            intracellular.Cell.insert1(cell_key, ignore_extra_fields = True)
            print(f'\tInsert Cell: {cell_id}')

    # ==================== Photo stimulation ====================
    if isinstance(meta_data.photostim, sio.matlab.mio5_params.mat_struct):
        photostimInfo = meta_data.photostim
        brain_region = re.split(',\s?|\s', photostimInfo.photostim_atlas_location)[1]
        coord_ap_ml_dv = re.findall('\d+.\d+', photostimInfo.photostim_coord_location)

        brain_location = {'brain_region': brain_region,
                          'brain_subregion': 'N/A',
                          'cortical_layer': 'N/A',
                          'hemisphere': hemisphere,
                          'brain_location_full_name': photostimInfo.photostim_atlas_location}
        # -- BrainLocation
        reference.BrainLocation.insert1(brain_location, skip_duplicates=True)
        # -- ActionLocation
        action_location = dict(brain_location,
                               coordinate_ref = 'bregma',
                               coordinate_ap = round(Decimal(coord_ap_ml_dv[0]), 2),
                               coordinate_ml = round(Decimal(coord_ap_ml_dv[1]), 2),
                               coordinate_dv = round(Decimal('0'), 2))  # no depth information for photostim
        reference.ActionLocation.insert1(action_location, ignore_extra_fields=True, skip_duplicates=True)

        # -- Device
        stim_device = 'laser'  # hard-coded here, could not find a more specific name from metadata
        stimulation.PhotoStimDevice.insert1({'device_name': stim_device}, skip_duplicates=True)

        # -- PhotoStimulationInfo
        stim_lambda = float(re.match('\d+', getattr(photostimInfo, 'lambda')).group())
        photim_stim_protocol = dict(protocol='_'.join([photostimInfo.stimulation_method, str(stim_lambda)]),
                                    device_name=stim_device,
                                    photo_stim_excitation_lambda=stim_lambda,
                                    photo_stim_method=photostimInfo.stimulation_method)
        stimulation.PhotoStimulationProtocol.insert1(photim_stim_protocol,
                                                     ignore_extra_fields=True, skip_duplicates=True)

        if dict(session_info, photostim_datetime = session_info['session_time']) not in stimulation.PhotoStimulation.proj():
            stimulation.PhotoStimulation.insert1(dict({**subject_info, **session_info,
                                                       **action_location, **photim_stim_protocol},
                                                      photostim_datetime = session_info['session_time']),
                                                 ignore_extra_fields = True)
            print(f'\tInsert Photo-Stimulation')

    # ==================== Virus ====================
    if isinstance(meta_data.virus, sio.matlab.mio5_params.mat_struct):
        virus_info = dict(
            virus_source=meta_data.virus.virus_source,
            virus=meta_data.virus.virus_name,
            virus_lot_number=meta_data.virus.virus_lot_number if meta_data.virus.virus_lot_number.size != 0 else '',
            virus_titer=meta_data.virus.titer.replace('x10', '') if len(meta_data.virus.titer) > 0 else None)
        virus.Virus.insert1(virus_info, skip_duplicates=True)

        # -- BrainLocation
        brain_location = {'brain_region': meta_data.virus.atlas_location.split(' ')[0],
                          'brain_subregion': meta_data.virus.virus_coord_location,
                          'cortical_layer': 'N/A',
                          'hemisphere': hemisphere}
        reference.BrainLocation.insert1(brain_location, skip_duplicates=True)

        virus_injection = dict(
            {**virus_info, **subject_info, **brain_location},
            coordinate_ref='bregma',
            injection_date=utilities.parse_date(meta_data.virus.injection_date))

        virus.VirusInjection.insert([dict(virus_injection,
                                          injection_depth = round(Decimal(re.match('\d+', depth).group()), 2),
                                          injection_volume = round(Decimal(re.match('\d+', vol).group()), 2))
                                     for depth, vol in zip(meta_data.virus.depth, meta_data.virus.volume)],
                                    ignore_extra_fields=True, skip_duplicates=True)
        print(f'\tInsert Virus Injections - Count: {len(meta_data.virus.depth)}')
