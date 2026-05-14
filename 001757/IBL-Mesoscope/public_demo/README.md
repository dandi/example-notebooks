# IBL - Mesoscopic Imaging Data

This example notebook demonstrates how to access the dataset published at [DANDI:001757](https://dandiarchive.org/dandiset/001757/draft).

This project aims to generate a rich, large-scale dataset capturing the activity of defined neural populations during the IBL decision-making task, using a 2-photon random access mesoscope. By imaging calcium activity in excitatory neurons across the dorsal cortex of transgenic mice, we seek to characterize how population-level neural activity encodes key task variables such as stimulus, choice, and bias context. Imaging functionally connected regions simultaneously allows us to investigate interregional interactions and trial-to-trial dynamics, while repeated recordings across days will help assess the stability of these neural representations over time and their relationship to expert performance.

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001757/IBL-Mesoscope
conda env create --file environment.yml
conda activate 001757_demo
```
