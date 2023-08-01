import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import re
import scipy.io as sio
from tqdm import tqdm
import pathlib
import numpy as np
import datajoint as dj

from pipeline import lab, experiment, ephys, virus
from pipeline import parse_date


dj.config['safemode'] = False


def main(meta_data_dir='./data/meta_data', reingest=True):
    meta_data_dir = pathlib.Path(meta_data_dir)
    if not meta_data_dir.exists():
        raise FileNotFoundError(f'Path not found!! {meta_data_dir.as_posix()}')

    # ==================== DEFINE CONSTANTS =====================

    # ---- inferred from paper ----
    hemi = 'left'
    skull_reference = 'bregma'
    photostim_devices = {473: 'LaserGem473', 594: 'LaserCoboltMambo100',  596: 'LaserCoboltMambo100'}

    # ---- from lookup ----
    probe = 'A4x8-5mm-100-200-177'
    electrode_config_name = 'silicon32'
    project_name = 'li2015'

    # ================== INGESTION OF METADATA ==================

    # ---- delete all Sessions ----
    if reingest:
        (experiment.Session & (experiment.ProjectSession & {'project_name': project_name}).fetch('KEY')).delete()

    # ---- insert metadata ----
    meta_data_files = meta_data_dir.glob('*.mat')
    for meta_data_file in tqdm(meta_data_files):
        print(f'-- Read {meta_data_file} --')
        meta_data = sio.loadmat(meta_data_file, struct_as_record=False, squeeze_me=True)['meta_data']

        # ==================== person ====================
        person_key = dict(username=meta_data.experimenters,
                          fullname=meta_data.experimenters)
        lab.Person.insert1(person_key, skip_duplicates=True)

        # ==================== subject gene modification ====================
        modified_genes = (meta_data.animalGeneModification
                          if isinstance(meta_data.animalGeneModification, (np.ndarray, list))
                          else [meta_data.animalGeneModification])
        lab.ModifiedGene.insert((dict(gene_modification=g, gene_modification_description=g)
                                 for g in modified_genes), skip_duplicates=True)

        # ==================== subject strain ====================
        animal_strains = (meta_data.animalStrain
                          if isinstance(meta_data.animalStrain, (np.ndarray, list))
                          else [meta_data.animalStrain])
        lab.AnimalStrain.insert(zip(animal_strains), skip_duplicates=True)

        # ==================== subject ====================
        animal_id = (meta_data.animalID[0]
                     if isinstance(meta_data.animalID, (np.ndarray, list)) else meta_data.animalID)
        animal_source = (meta_data.animalSource[0]
                         if isinstance(meta_data.animalSource, (np.ndarray, list)) else meta_data.animalSource)
        subject_key = dict(subject_id=int(re.search('\d+', animal_id).group()),
                           sex=meta_data.sex[0].upper() if len(meta_data.sex) != 0 else 'U',
                           species=meta_data.species,
                           animal_source=animal_source)
        try:
            date_of_birth = parse_date(meta_data.dateOfBirth)
            subject_key['date_of_birth'] = date_of_birth
        except:
            pass

        lab.AnimalSource.insert1((animal_source,), skip_duplicates=True)

        with lab.Subject.connection.transaction:
            if subject_key not in lab.Subject.proj():
                lab.Subject.insert1(subject_key)
                lab.Subject.GeneModification.insert((dict(subject_key, gene_modification=g) for g in modified_genes),
                                                     ignore_extra_fields=True)
                lab.Subject.Strain.insert((dict(subject_key, animal_strain=strain) for strain in animal_strains),
                                                     ignore_extra_fields=True)

        # ==================== session ====================
        session_key = dict(subject_key, username=person_key['username'],
                           session=len(experiment.Session & subject_key) + 1,
                           session_date=parse_date(meta_data.dateOfExperiment + ' ' + meta_data.timeOfExperiment))
        experiment.Session.insert1(session_key, ignore_extra_fields=True)
        experiment.ProjectSession.insert1({**session_key, 'project_name': project_name}, ignore_extra_fields=True)

        print(f'\tInsert Session - {session_key["subject_id"]} - {session_key["session_date"]}')

        # ==================== Probe Insertion ====================
        brain_location_key = dict(brain_area=meta_data.extracellular.recordingLocation,
                                  hemisphere=hemi)
        insertion_loc_key = dict(skull_reference=skull_reference,
                                 ap_location=meta_data.extracellular.recordingCoordinates[0] * 1000,  # mm to um
                                 ml_location=meta_data.extracellular.recordingCoordinates[1] * 1000,  # mm to um
                                 dv_location=meta_data.extracellular.recordingCoordinates[2] * -1)    # already in um

        with ephys.ProbeInsertion.connection.transaction:
            ephys.ProbeInsertion.insert1(dict(session_key, insertion_number=1, probe=probe,
                                              electrode_config_name=electrode_config_name), ignore_extra_fields=True)
            ephys.ProbeInsertion.InsertionLocation.insert1(dict(session_key, **insertion_loc_key,
                                                                insertion_number=1),
                                                           ignore_extra_fields=True)
            ephys.ProbeInsertion.RecordableBrainRegion.insert1(dict(session_key, **brain_location_key,
                                                                    insertion_number=1),
                                                               ignore_extra_fields=True)
            ephys.ProbeInsertion.ElectrodeSitePosition.insert((dict(
                session_key, insertion_number=1, probe=probe, electrode_config_name=electrode_config_name,
                electrode_group=0, electrode= site_idx + 1,
                electrode_posx=x*1000, electrode_posy=y*1000, electrode_posz=z*1000)
                for site_idx, (x, y, z) in enumerate(meta_data.extracellular.siteLocations)),
                ignore_extra_fields=True)

        print(f'\tInsert ProbeInsertion - Location: {brain_location_key}')

        # ==================== Virus ====================
        if 'virus' in meta_data._fieldnames and isinstance(meta_data.virus, sio.matlab.mio5_params.mat_struct):
            virus_info = dict(
                virus_source=meta_data.virus.virusSource,
                virus=meta_data.virus.virusID,
                virus_lot_number=meta_data.virus.virusLotNumber if len(meta_data.virus.virusLotNumber) != 0 else '',
                virus_titer=meta_data.virus.virusTiter.replace('x10', '') if meta_data.virus.virusTiter != 'untitered' else None)
            virus.Virus.insert1(virus_info, skip_duplicates=True)

            # -- BrainLocation
            brain_location_key = dict(brain_area=meta_data.virus.infectionLocation,
                                      hemisphere=hemi)
            virus_injection = dict(
                {**virus_info, **subject_key, **brain_location_key},
                injection_date=parse_date(meta_data.virus.injectionDate))

            virus.VirusInjection.insert([dict(virus_injection,
                                              injection_id=inj_idx + 1,
                                              ap_location=coord[0] * 1000,
                                              ml_location=coord[1] * 1000,
                                              dv_location=coord[2] * 1000 * -1,
                                              injection_volume=vol)
                                         for inj_idx, (coord, vol) in enumerate(zip(meta_data.virus.infectionCoordinates,
                                                                                    meta_data.virus.injectionVolume))],
                                        ignore_extra_fields=True, skip_duplicates=True)
            print(f'\tInsert Virus Injections - Count: {len(meta_data.virus.injectionVolume)}')

        # ==================== Photostim ====================
        if 'photostim' in meta_data._fieldnames and isinstance(meta_data.photostim, sio.matlab.mio5_params.mat_struct):
            photostimLocation = (meta_data.photostim.photostimLocation
                                 if isinstance(meta_data.photostim.photostimLocation, np.ndarray)
                                 else np.array([meta_data.photostim.photostimLocation]))
            photostimCoordinates = (meta_data.photostim.photostimCoordinates
                                    if isinstance(meta_data.photostim.photostimCoordinates[0], np.ndarray)
                                    else np.array([meta_data.photostim.photostimCoordinates]))
            photostim_locs = []
            for ba in set(photostimLocation):
                coords = photostimCoordinates[photostimLocation == ba]
                photostim_locs.append((ba, coords))

            for stim_idx, (loc, coords) in enumerate(photostim_locs):

                experiment.Photostim.insert1(dict(
                    session_key, photo_stim=stim_idx + 1,
                    photostim_device=photostim_devices[meta_data.photostim.photostimWavelength]),
                    ignore_extra_fields=True)

                experiment.Photostim.PhotostimLocation.insert([
                    dict(session_key,  photo_stim=stim_idx + 1,
                         brain_area=loc, skull_reference=skull_reference,
                         ap_location=coord[0] * 1000,
                         ml_location=coord[1] * 1000,
                         dv_location=coord[2] * 1000 * -1) for coord in coords], ignore_extra_fields=True)

            print(f'\tInsert Photostim - Count: {len(photostim_locs)}')

    experiment.PhotostimBrainRegion.populate(display_progress=True)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
