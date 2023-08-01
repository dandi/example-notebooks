
import numpy as np

import matplotlib.pyplot as plt

from pipeline.psth import TrialCondition
from pipeline.psth import UnitPsth
from pipeline import ephys, experiment
from pipeline.plot.util import _get_photostim_time_and_duration, _get_trial_event_times, _get_units_hemisphere


_plt_xlim = [-3, 2]


def _plot_spike_raster(ipsi, contra, vlines=[], shade_bar=None, ax=None, title='', xlim=_plt_xlim):
    if not ax:
       fig, ax = plt.subplots(1, 1)

    ipsi_tr = ipsi['raster'][1]
    for i, tr in enumerate(set(ipsi['raster'][1])):
        ipsi_tr = np.where(ipsi['raster'][1] == tr, i, ipsi_tr)

    contra_tr = contra['raster'][1]
    for i, tr in enumerate(set(contra['raster'][1])):
        contra_tr = np.where(contra['raster'][1] == tr, i, contra_tr)

    ax.plot(ipsi['raster'][0], ipsi_tr, 'r.', markersize=1)
    ax.plot(contra['raster'][0], contra_tr + ipsi_tr.max() + 1, 'b.', markersize=1)

    for x in vlines:
        ax.axvline(x=x, linestyle='--', color='k')
    if shade_bar is not None:
        ax.axvspan(shade_bar[0], shade_bar[0] + shade_bar[1], alpha=0.3, color='royalblue')

    ax.set_axis_off()
    ax.set_xlim(xlim)
    ax.set_title(title)


def _plot_psth(ipsi, contra, vlines=[], shade_bar=None, ax=None, title='', xlim=_plt_xlim):
    if not ax:
       fig, ax = plt.subplots(1, 1)

    ax.plot(contra['psth'][1], contra['psth'][0], 'b')
    ax.plot(ipsi['psth'][1], ipsi['psth'][0], 'r')

    for x in vlines:
        ax.axvline(x=x, linestyle='--', color='k')
    if shade_bar is not None:
        ax.axvspan(shade_bar[0], shade_bar[0] + shade_bar[1], alpha=0.3, color='royalblue')

    ax.set_ylabel('spikes/s')
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.set_xlim(xlim)
    ax.set_xlabel('Time (s)')
    ax.set_title(title)


def plot_unit_psth(unit_key, condition_name_kw=['good_noearlylick_', '_hit'], axs=None, title='', xlim=_plt_xlim):
    """
    Default raster and PSTH plot for a specified unit - only {good, no early lick, correct trials} selected
    condition_name_kw: list of keywords to match for the TrialCondition name
    """

    hemi = _get_units_hemisphere(unit_key)

    ipsi_cond_name = TrialCondition.get_cond_name_from_keywords(condition_name_kw
                                                                + ['left' if hemi == 'left' else 'right'])[0]
    contra_cond_name = TrialCondition.get_cond_name_from_keywords(condition_name_kw
                                                                  + ['right' if hemi == 'left' else 'left'])[0]

    ipsi_hit_unit_psth = UnitPsth.get_plotting_data(
        unit_key, {'trial_condition_name': ipsi_cond_name})

    contra_hit_unit_psth = UnitPsth.get_plotting_data(
        unit_key, {'trial_condition_name': contra_cond_name})

    # get event start times: sample, delay, response
    trial_cond_name = TrialCondition.get_cond_name_from_keywords(condition_name_kw)[0]
    period_starts = _get_trial_event_times(['sample', 'delay', 'go'], unit_key, trial_cond_name)

    # photostim shaded bar (if applicable)
    try:
        stim_trial_cond_name = TrialCondition.get_cond_name_from_keywords(condition_name_kw + ['_stim'])[0]
        stim_bar = _get_photostim_time_and_duration(unit_key, TrialCondition().get_trials(stim_trial_cond_name))
    except:
        stim_bar = None

    if axs is None:
        fig, axs = plt.subplots(2, 1)

    _plot_spike_raster(ipsi_hit_unit_psth, contra_hit_unit_psth, ax=axs[0],
                       vlines=period_starts, shade_bar=stim_bar,
                       title=title if title else f'Unit #: {unit_key["unit"]}', xlim=xlim)
    _plot_psth(ipsi_hit_unit_psth, contra_hit_unit_psth,
               vlines=period_starts, shade_bar=stim_bar, ax=axs[1], xlim=xlim)

