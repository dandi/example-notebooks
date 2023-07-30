import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import itertools

from pipeline import lab, experiment, psth
from pipeline import dict_to_hash


# ================== DEFINE LOOK-UP ==================

# ==================== Project =====================

experiment.Project.insert([('li2015', '', 'doi:10.1038/nature14178'),
                           ('lidaie2016', '', 'doi:10.1038/nature17643')],
                          skip_duplicates=True)

# ==================== Probe =====================
# Probe - NeuroNexus Silicon Probe
probe = 'A4x8-5mm-100-200-177'
lab.Probe.insert1({'probe': probe,
                   'probe_type': 'nn_silicon_probe',
                   'probe_comment': 'NeuroNexus silicon probes (part no. A4x8-5mm-100-200-177). The 32 channel voltage signals were multiplexed, recorded on a PCI6133 board at 312.5 kHz (National instrument), and digitized at 14 bit. The signals were demultiplexed into the 32 voltage traces, sampled at 19531.25 Hz and stored for offline analyses.'},
                  skip_duplicates=True)
lab.Probe.Electrode.insert(({'probe': probe, 'electrode': x} for x in range(1, 33)), skip_duplicates=True)

electrode_group = {'probe': probe, 'electrode_group': 0}
electrode_group_member = [{**electrode_group, 'electrode': chn} for chn in range(1, 33)]
electrode_config_name = 'silicon32'  #
electrode_config_hash = dict_to_hash(
    {**electrode_group, **{str(idx): k for idx, k in enumerate(electrode_group_member)}})
lab.ElectrodeConfig.insert1({'probe': probe,
                             'electrode_config_hash': electrode_config_hash,
                             'electrode_config_name': electrode_config_name}, skip_duplicates=True)
lab.ElectrodeConfig.ElectrodeGroup.insert1({'electrode_config_name': electrode_config_name,
                                            **electrode_group}, skip_duplicates=True)
lab.ElectrodeConfig.Electrode.insert(({'electrode_config_name': electrode_config_name, **member}
                                     for member in electrode_group_member), skip_duplicates=True)

# ==================== Photostim Trial Condition =====================

stim_locs = [('left', 'alm'), ('right', 'alm'), ('bilateral', 'alm')]
stim_periods = [None, 'sample', 'early_delay', 'middle_delay']

trial_conditions = []
for hemi, brain_area in stim_locs:
    for instruction in (None, 'left', 'right'):
        for period, stim_dur in itertools.product(stim_periods, (0.5, 0.8)):
            condition = {'trial_condition_name': '_'.join(filter(None, ['all', 'noearlylick', '_'.join([hemi, brain_area]),
                                                                        period, str(stim_dur), 'stim', instruction])),
                         'trial_condition_func': '_get_trials_include_stim',
                         'trial_condition_arg': {
                             **{'_outcome': 'ignore',
                                'task': 'audio delay',
                                'task_protocol': 1,
                                'early_lick': 'no early',
                                'stim_laterality': hemi,
                                'stim_brain_area': brain_area},
                             **({'trial_instruction': instruction} if instruction else {'_trial_instruction': 'non-performing'}),
                             **({'photostim_period': period, 'duration': stim_dur} if period else dict())}}
            trial_conditions.append(condition)

psth.TrialCondition.insert_trial_conditions(trial_conditions)

