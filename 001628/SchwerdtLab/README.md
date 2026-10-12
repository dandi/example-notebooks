# Microinvasive Probes for Monitoring Electrical and Chemical Neural Activity in Nonhuman Primates

These example notebooks demonstrate how to access the dataset published at [DANDI:001628](https://dandiarchive.org/dandiset/001628/draft\).

This dandiset contains in vivo fast-scan cyclic voltammetry (FSCV) sessions and electrophysiology (EPhys) sessions from micro-invasive probes chronically implanted in the striatum of task-performing rhesus monkeys. 
**FSCV and EPhys were recorded in separate sessions** (i.e., a given NWB file/session contains either FSCV or EPhys as the primary recording modality, not both simultaneously).

## Tutorials

- [`001628_ephys_tutorial.ipynb`](./001628_ephys_tutorial.ipynb): Access an example **EPhys** NWB file (raw `ElectricalSeries`, processed traces in `processing/ecephys`, and behavioral data such as eye tracking, trials, and events).
- [`001628_fscv_tutorial.ipynb`](./001628_fscv_tutorial.ipynb): Access an example **FSCV** NWB file (raw `FSCVResponseSeries` in `acquisition`, excitation waveform in `stimulus`, derived trial-aligned FSCV signals in `processing/fscv`, and behavioral data such as eye tracking, trials, and events).

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001628/SchwerdtLab
conda env create --file environment.yml
conda activate schwerdtlab_001628_demo
```

## Running the notebook

```bash
jupyter notebook 001628_ephys_tutorial.ipynb
# or
jupyter notebook 001628_fscv_tutorial.ipynb
```
