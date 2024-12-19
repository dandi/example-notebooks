# Offline ensemble co-reactivation links memories across days

This example notebook demonstrates how to access the dataset published at [DANDI:000718](https://dandiarchive.org/dandiset/000718/draft).

This dataset contains calcium imaging and EEG/EMG recordings. Freezing behavior analysis and sleep classification output is also available for some sessions.
A week-long recording of EEG/EMG data is stored in nwbfile with session_id = "Week". This type of session contains also cell registration output.

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/000718/CaiLab
conda env create --file environment.yml
conda activate cailab_000718_demo
```

## Running the notebook

```bash
jupyter notebook 000718_demo.ipynb
```
