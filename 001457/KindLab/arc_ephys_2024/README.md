# Fear Conditioning Neural and Behavioral Responses in Syngap1+/Delta-GAP Rats: LFP, EEG, and Accelerometer Data

This example notebook demonstrates how to access the dataset published at [DANDI:001457](https://dandiarchive.org/dandiset/001457/draft).

The experiment investigated fear conditioning in male wild-type and Syngap+/Delta-GAP rats (n=31, ages 3-6 months). Recordings included Local Field Potentials (LFP), electroencephalogram (EEG), head-mounted accelerometer data, and behavioral video recordings across five experimental days. The protocol involved context habituation, seizure screening, and a fear conditioning paradigm where rats were exposed to blue flashing light (5 Hz, 110 lux) paired with foot shocks. Data were collected using OpenEphys software and a 16-channel Intan digitizing head stage. Behavioral paradigm triggers were managed using FreezeFrame software, and behavioral cameras recorded rat movements throughout the experimental sessions. The experimental design allowed for assessing neural responses, seizure occurrence, and fear learning in these genetic variants.

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001457/KindLab
conda env create --file environment.yml
conda activate kindlab_001457_demo
```

## Running the notebook

```bash
jupyter notebook 001457_demo.ipynb
```
