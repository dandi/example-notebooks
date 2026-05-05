# Turner Lab M1 MPTP Parkinsonism Dataset

This folder contains example notebooks for [DANDI:001636](https://dandiarchive.org/dandiset/001636), single-unit electrophysiology recordings from primary motor cortex (M1) of macaque monkeys performing flexion/extension motor tasks before and after MPTP-induced parkinsonism. Pyramidal tract neurons (PTNs) and corticostriatal neurons (CSNs) are identified by antidromic stimulation, allowing the comparison of how Parkinson's pathology affects each projection class.

Relevant publications:

- Pasquereau B, Turner RS (2011). Primary motor cortex of the parkinsonian monkey: differential effects on the spontaneous activity of pyramidal tract-type neurons. *Cerebral Cortex* 21(6): 1362-1378.
- Pasquereau B, Turner RS (2016). Movement encoding deficits in the motor cortex of parkinsonian macaque monkeys. *Brain*.

## Notebooks

- `turner_m1_usage.ipynb`: Entry-point usage guide. Streams NWB files from DANDI, walks through the file layout (units, kinematics, trials, antidromic sweeps, electrode metadata) and shows how to access each table.
- `turner_m1_peth.ipynb`: Builds peri-event time histograms aligned to behavioral events using [pynapple](https://pynapple.org), illustrating the `Ts`/`Tsd`/`TsGroup`/`IntervalSet` workflow for trial-aligned spike analysis.
- `turner_m1_glm.ipynb`: Fits Poisson GLMs that predict M1 spiking from kinematic features using [NeMoS](https://nemos.readthedocs.io/), with JAX `vmap` for vectorized fitting and shuffle-based significance testing, reproducing the encoding analysis from Pasquereau & Turner (Brain 2016).
- `antidromic_detection_tutorial.ipynb`: Background tutorial on antidromic stimulation and how the dataset uses it to classify PTNs vs CSNs, with worked examples on the Pasquereau & Turner (2011) recordings.

The two `.py` files (`notebook_helpers.py`, `trial_structure_plot.py`) are imported by the notebooks and must stay in the same directory.

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001636/TurnerLab/motor_cortex
conda env create --file environment.yml
conda activate turnerlab_001636_demo
```

## Running the notebooks

```bash
jupyter notebook
```
