import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import re
import scipy.io as sio
from tqdm import tqdm
import pathlib
import numpy as np
import datajoint as dj

from pipeline import lab, experiment, virus
from pipeline import parse_date


def main(meta_data_dir='/data/meta_data'):
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

    # ---- virus source mapper ----
    virus_source_mapper = {
        'Upenn core': 'UPenn',
        'Upenn Core': 'UPenn',
        'UPenn': 'UPenn'
    }

    # ---- brain location mapper ----
    brain_location_mapper = {
        'Left ALM': 'left_alm',
        'Left pontine nucleus': 'left_pons'
    }

    # ================== INGESTION OF METADATA ==================

    # ---- delete all Sessions ----
    experiment.Session.delete()

    # ---- insert metadata ----
    meta_data_files = meta_data_dir.glob('*.mat')
    for meta_data_file in tqdm(meta_data_files):
        print(f'-- Read {meta_data_file} --')
        meta_data = sio.loadmat(meta_data_file, struct_as_record = False, squeeze_me=True)['meta_data']

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
                           subject_nickname=re.search('meta_(an\d+)_', meta_data_file.stem).group(1),
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
                           session_date=parse_date(meta_data.dateOfExperiment))
        filename = meta_data_file.stem
        if re.search('fv(\d+)', filename):
            session_key.update(fov=int(re.search('fv(\d+)', filename).group(1)))

        experiment.Session.insert1(session_key, ignore_extra_fields=True)

        experiment.Session.ImagingDepth.insert1(
            dict(session_key, imaging_depth=int(re.search('_(\d+)(_fv|$)', filename).group(1))),
            ignore_extra_fields=True)

        print(f'\tInsert Session - {session_key["subject_id"]} - {session_key["session_date"]}')


        # ==================== Virus ====================
        if 'virus' in meta_data._fieldnames and isinstance(meta_data.virus, sio.matlab.mio5_params.mat_struct):
            virus_info = dict(
                virus_source=virus_source_mapper[meta_data.virus.Source],
                virus=meta_data.virus.ID[1],
                virus_titer=meta_data.virus.Titer.replace('x10', '') if meta_data.virus.Titer != 'unknown' else None)

            virus.Virus.insert1(virus_info, skip_duplicates=True)

            # -- BrainLocation
            brain_location_key = (experiment.BrainLocation & {'brain_location_name': brain_location_mapper[meta_data.virus.Location],
                                                              'hemisphere': hemi,
                                                              'skull_reference': skull_reference}).fetch1('KEY')
            virus_injection = dict(
                {**virus_info, **subject_key, **brain_location_key},
                injection_date=parse_date(meta_data.virus.injectionDate))

            virus.VirusInjection.insert([dict(virus_injection,
                                              injection_id=inj_idx + 1,
                                              virus_dilution=float(re.search('1:(\d+) dilution',
                                                                   meta_data.virus.Concentration).group(1)) \
                                                                       if 'Concentraion' in meta_data.virus._fieldnames else None,
                                              ml_location=coord[0] * 1000,
                                              ap_location=coord[1] * 1000,
                                              dv_location=coord[2] * 1000,
                                              injection_volume=vol)
                                         for inj_idx, (coord, vol) in enumerate(zip(meta_data.virus.Coordinates,
                                                                                    meta_data.virus.injectionVolume))],
                                        ignore_extra_fields=True, skip_duplicates=True)
            print(f'\tInsert Virus Injections - Count: {len(meta_data.virus.injectionVolume)}')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
