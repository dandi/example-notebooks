# Aseptic, semi-sealed cranial chamber implants for chronic multi-channel neurochemical and electrophysiological neural recording in nonhuman primates
This tutorial demonstrates how to access an NWB file from [DANDI:001267](https://dandiarchive.org/dandiset/001627/draft) for the study detailed in [_"Aseptic, semi-sealed cranial chamber implants for chronic multi-channel neurochemical and electrophysiological neural recording in nonhuman primates"_](https://www.biorxiv.org/content/10.1101/2025.01.30.635139v1.full.pdf).

This dataset contains an experimental session with simultaneous recordings of **fast-scan cyclic voltammetry (FSCV)** and **electrophysiology (EPhys)** from the striatum of a task-performing rhesus monkey.
## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001627/SchwerdtLab
conda env create --file environment.yml
conda activate schwerdtlab_001627_demo
```

## Running the notebook

```bash
jupyter notebook 001627_fscv_ephys_tutorial.ipynb
```
