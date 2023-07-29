'''
This script ingests all the data for photo-activation experiments.
'''

import datajoint as dj
import scipy.io as sio
import numpy as np
import os
import glob
import re
from datetime import datetime
from pipeline import reference, subject, action, acquisition, behavior, ephys

# insert the meta data
print('Ingesting meta data...')
files1 = glob.glob('/data/datafiles/meta_data*')
files2 = glob.glob('/data/datafiles 2/meta_data*')
files = np.hstack([files1, files2])


for file in files:
    data = \
        sio.loadmat(file, struct_as_record=False, squeeze_me=True)['meta_data']

    # ====== reference tables ======
    reference.AnimalSource.insert1([data.animalSource], skip_duplicates=True)
    reference.WhiskerConfig.insert1([data.whiskerConfig], skip_duplicates=True)
    reference.Experimenter.insert1([data.experimenters], skip_duplicates=True)
    reference.ReferenceAtlas.insert1([data.referenceAtlas],
                                     skip_duplicates=True)

    # ====== subject tables ======
    subject.Species.insert1([data.species], skip_duplicates=True)

    animal = {
        'subject': data.animalID,
        'species': data.species,
        'sex': data.sex,
        'date_of_birth': data.dateOfBirth,
        'animal_source': data.animalSource
    }
    subject.Subject.insert1(animal, skip_duplicates=True)

    zygosity = {'subject': data.animalID}
    alleles = data.animalGeneModification
    if alleles.size > 0:
        strains = data.animalStrain
        if type(strains) == str:
            strains = [strains]
        for i_allele, allele in enumerate(alleles):
            strain = str(strains[i_allele])
            subject.Allele.insert1([allele, strain], skip_duplicates=True)
            zygosity['allele'] = allele
            copy = data.animalGeneCopy[i_allele]
            if copy == 0:
                zygosity['zygosity'] = 'Negative'
            elif copy == 1:
                zygosity['zygosity'] = 'Heterozygous'
            elif copy == 2:
                zygosity['zygosity'] = 'Homozygous'
            else:
                print('Invalid zygosity')
                continue
            subject.Zygosity.insert1(zygosity, skip_duplicates=True)

    # ====== action tables ======
    if data.weightBefore.size > 0 and data.weightAfter > 0:
        weighing = {
            'subject': data.animalID,
            'weight_before': data.weightBefore,
            'weight_after': data.weightAfter
        }
        action.Weighing.insert1(weighing, skip_duplicates=True)

    whisker = {
        'subject': data.animalID,
        'whisker_config': data.whiskerConfig
    }
    action.SubjectWhiskerConfig.insert1(whisker, skip_duplicates=True)

    # virus related tables
    if hasattr(data, 'virus'):
        reference.VirusSource.insert1([data.virus.virusSource],
                                      skip_duplicates=True)
        virus = {
            'virus': data.virus.virusID,
            'virus_source': data.virus.virusSource
        }
        reference.Virus.insert1(virus, skip_duplicates=True)

        location = data.virus.infectionLocation
        words = re.sub("[^\w]", " ", location).split()
        hemisphere = np.array(words)[np.array([(word in ['left', 'right'])
                                              for word in words])]
        loc = np.array(words)[np.array([
            (word in ['Fastigial', 'Dentate', 'DCN', 'ALM']) for word in words
            ])]
        ref = np.array(words)[np.array([
            (word in ['lambda', 'bregma']) for word in words
            ])]
        virus_injection = {
            'subject': data.animalID,
            'virus': data.virus.virusID,
            'brain_location': str(np.squeeze(loc)),
            'hemisphere': str(np.squeeze(hemisphere)),
            'injection_volume': data.virus.injectionVolume,
            'injection_date': datetime.strptime(data.virus.injectionDate,
                                                '%Y%m%d').date(),
            'injection_coordinate_ap': data.virus.infectionCoordinates[0],
            'injection_coordinate_ml': data.virus.infectionCoordinates[1],
            'injection_coordinate_dv': data.virus.infectionCoordinates[2],
            'coordinate_ref': str(np.squeeze(ref))
        }
        action.VirusInjection.insert1(virus_injection, skip_duplicates=True)

    # ExtraCellular recording related tables
    probe_sources = data.extracellular.probeSource
    probes = data.extracellular.probeType

    if type(probe_sources) == str:
        reference.ProbeSource.insert1([probe_sources], skip_duplicates=True)
        n_channels = int(np.squeeze(re.findall('\s\d{2}', probes)))
        probe_key = {
            'probe_type': probes,
            'probe_source': probe_sources,
            'channel_counts': n_channels
        }
        reference.Probe.insert1(probe_key, skip_duplicates=True)
    else:
        for iprobe, probe_source in enumerate(probe_sources):
            reference.ProbeSource.insert1([probe_source], skip_duplicates=True)
            probe = probes[iprobe]
            n_channels = int(np.squeeze(re.findall('\s\d{2}', probe)))
            probe_key = {
                'probe_type': probe,
                'probe_source': probe_source,
                'channel_counts': n_channels
            }
            reference.Probe.insert1(probe_key, skip_duplicates=True)

    # ===== acquisition tables ======
    # Session table and part tables
    dirs = file.partition('meta_data')
    session = {
        'subject': data.animalID,
        'session_time': datetime.strptime(
            data.dateOfExperiment+data.timeOfExperiment, '%Y%m%d%H%M%S'),
        'session_directory': os.path.join(dirs[0], 'data_structure' + dirs[2])
    }
    acquisition.Session.insert1(session, skip_duplicates=True)

    session_experimenter = (acquisition.Session & session).fetch('KEY')[0]
    session_experimenter['experimenter'] = data.experimenters
    acquisition.Session.Experimenter.insert1(session_experimenter,
                                             skip_duplicates=True)

    session_type = (acquisition.Session & session).fetch('KEY')[0]
    if type(data.experimentType) is str:
        session_type['experment_type'] = data.experimentType
        acquisition.ExperimentType.insert1([data.experimentType],
                                           skip_duplicates=True)
        acquisition.Session.ExperimentType.insert1(session_type,
                                                   skip_duplicates=True)
    for exp_type in data.experimentType:
        session_type['experiment_type'] = exp_type
        acquisition.ExperimentType.insert1([exp_type], skip_duplicates=True)
        acquisition.Session.ExperimentType.insert1(session_type,
                                                   skip_duplicates=True)

    # PhotoStim table
    photo_stim = (acquisition.Session & session).fetch('KEY')[0]
    location = data.photostim.photostimLocation
    words = re.sub("[^\w]", " ", location).split()
    hemisphere = np.array(words)[np.array(
        [(word in ['left', 'right']) for word in words])]
    loc = np.array(words)[np.array(
        [(word in ['Fastigial', 'Dentate', 'DCN', 'ALM']) for word in words])]
    photo_stim.update({
        'photo_stim_wavelength': data.photostim.photostimWavelength,
        'photo_stim_method': data.photostim.stimulationMethod,
        'brain_location': str(np.squeeze(loc)),
        'hemisphere': str(np.squeeze(hemisphere)),
        'coordinate_ref': 'lambda',
        'photo_stim_coordinate_ap': data.photostim.photostimCoordinates[0],
        'photo_stim_coordinate_ml': data.photostim.photostimCoordinates[1],
        'photo_stim_coordinate_dv': data.photostim.photostimCoordinates[2]
    })
    acquisition.PhotoStim.insert1(photo_stim, skip_duplicates=True)

    # ===== ephys tables =====
    # ProbeInsertion
    probe_insertion = (acquisition.Session & session).fetch('KEY')[0]
    probe_type = data.extracellular.probeType

    # to be changed when metadata is fixed
    if type(probe_type) is not str:
        probe_type = probe_type[0]

    probe_insertion.update({
        'probe_type': probe_type,
        'brain_location': data.extracellular.recordingLocation,
        'rec_coordinate_ap': data.extracellular.recordingCoordinates[0],
        'rec_coordinate_ml': data.extracellular.recordingCoordinates[1],
        'ground_coordinate_ap': data.extracellular.groundCoordinates[0],
        'ground_coordinate_ml': data.extracellular.groundCoordinates[1],
        'ground_coordinate_dv': data.extracellular.groundCoordinates[2],
        'rec_marker': data.extracellular.recordingMarker,
        'coordinate_ref': 'lambda',
        'penetration_num': data.extracellular.penetrationN,
        'spike_sorting_method': data.extracellular.spikeSorting,
        'ad_unit': data.extracellular.ADunit,
        'rec_marker': data.extracellular.recordingMarker
    })
    ephys.ProbeInsertion.insert1(probe_insertion, skip_duplicates=True)

# populate imported tables
print('Populating behavior and ephys tables...')
kargs = dict(
    display_progress=True,
    suppress_errors=True
)
behavior.TrialSet.populate(**kargs)
behavior.TrialSetType.populate(**kargs)
ephys.UnitSpikeTimes.populate(**kargs)
behavior.TrialNumberSummary.populate(**kargs)
ephys.UnitSelectivity.populate(**kargs)
ephys.AlignedPsthStimOn.populate(**kargs)
ephys.PsthForCodingDirection.populate(**kargs)
ephys.CodingDirection.populate(**kargs)
ephys.ProjectedPsthTraining.populate(**kargs)
ephys.ProjectedPsth.populate(**kargs)
