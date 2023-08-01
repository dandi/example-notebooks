import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..', '..'))

from pipeline import intracellular, extracellular, analysis, behavior, stimulation


settings = {'reserve_jobs': True, 'suppress_errors': True, 'display_progress': False}

# ============= Extracellular =============
# -- Ingest unit spike times
extracellular.UnitSpikeTimes.populate(**settings)
# -- UnitSpikeTimes trial-segmentation
analysis.RealignedEvent.populate(**settings)
extracellular.TrialSegmentedUnitSpikeTimes.populate(**settings)

# ============= Intracellular =============
intracellular.MembranePotential.populate(**settings)
intracellular.CurrentInjection.populate(**settings)
# -- Behavioral
behavior.LickTrace.populate(**settings)
# -- Perform trial segmentation
intracellular.TrialSegmentedMembranePotential.populate(**settings)
intracellular.TrialSegmentedCurrentInjection.populate(**settings)
stimulation.TrialSegmentedPhotoStimulus.populate(**settings)
