# Analysis Notebooks for Zhai et al. 2025

## Goal

This submission provides Jupyter notebooks for reproducing key figures from **Zhai et al. 2025** using data from **DANDI:001538 - State-dependent modulation of spiny projection neurons controls levodopa-induced dyskinesia**. The notebooks demonstrate how to analyze electrophysiology, optogenetics, and acetylcholine biosensor data to understand cellular mechanisms underlying levodopa-induced dyskinesia in Parkinson's disease.

## Publication

**Zhai et al. 2025** - *State-dependent modulation of spiny projection neurons controls levodopa-induced dyskinesia*

## Notebooks

### `how_to_use_this_dataset.ipynb`
Introduction and data exploration tutorial showing how to access and browse the NWB files in DANDI:001538, extract metadata, and perform basic data visualization.

### `figure_1E_dspn_somatic_excitability.ipynb`
Reproduces Figure 1E analyzing somatic excitability in direct pathway striatal projection neurons (dSPNs). Generates frequency-intensity curves and rheobase measurements from current clamp recordings to show L-DOPA treatment effects on neuronal excitability.

### `figure_2GH_oepsc_analysis.ipynb`
Reproduces Figure 2G-H analyzing optogenetically-evoked postsynaptic currents (oEPSCs). Compares amplitude distributions and mean responses between off-state and on-state conditions using ChR2 optogenetic stimulation and voltage-clamp recordings.

### `figure_5F_acetylcholine_biosensor.ipynb`
Reproduces Figure 5F analyzing acetylcholine release dynamics using the GRABACh3.0 biosensor. Shows acetylcholine signaling alterations across control, Parkinsonian, and dyskinetic conditions with pharmacological modulation (dopamine, quinpirole, sulpiride).