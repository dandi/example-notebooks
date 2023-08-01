from pipeline import (reference, subject, acquisition, stimulation, analysis, virus,
                      intracellular, behavior, utilities)

# ====================== Settings ======================
settings = {'reserve_jobs': True, 'suppress_errors': True, 'display_progress': False}

# ====================== Starting import and compute procedure ======================
# -- TrialSet
acquisition.TrialSet.populate(**settings)
# -- Ephys
intracellular.MembranePotential.populate(**settings)
intracellular.SpikeTrain.populate(**settings)
# -- Behavioral
behavior.Behavior.populate(**settings)
# -- Perform trial segmentation
print('------- Perform trial segmentation -------')
analysis.RealignedEvent.populate(**settings)
intracellular.TrialSegmentedMembranePotential.populate(**settings)
intracellular.TrialSegmentedSpikeTrain.populate(**settings)
behavior.TrialSegmentedBehavior.populate(**settings)
stimulation.TrialSegmentedPhotoStimulus.populate(**settings)

