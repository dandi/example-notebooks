# Targeted micro-fiber arrays for measuring and manipulating localized multi-scale neural dynamics over large, deep brain volumes during behavior tutorial

This example notebook demonstrates how to access the dataset published at [DANDI:001084](https://dandiarchive.org/dandiset/001084/draft).

This dataset contains fiber photometry recordings from multi-fiber arrays implanted in the striatum in mice running on 
a treadmill while receiving either visual (blue LED) or auditory (12 kHz tone) stimuli at random intervals (4–40 s). 
Some sessions may include water reward delivery, where a water spout mounted on a post delivered water rewards (9 μL) 
at random time intervals (randomly drawn from a 5-30s uniform distribution) through a water spout and solenoid valve 
gated electronically. Licking was monitored by a capacitive touch circuit connected to the spout.

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001084/HoweLab
conda env create --file environment.yml
conda activate howelab_001084_demo
```

## Running the notebook

```bash
jupyter notebook 001084_demo.ipynb
```
