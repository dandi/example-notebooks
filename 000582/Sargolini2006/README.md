# Educational notebook based on Sargolini 2006

This example notebook demonstrates how to access the dataset published in [Sargolini et al. (Science, 2006)](https://doi.org/10.1126/science.1125572) using `dandi`.
The dataset contains spike times for recorded grid cells from the Medial Entorhinal Cortex (MEC) in rats that explored two-dimensional environments. The behavioral data includes position from the tracking LED(s).

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/000582/Sargolini2006
conda env create --file environment.yml
conda activate sargolini-2006-env
```

## Running the notebook

```bash
jupyter notebook 000582_Sargolini2006_demo.ipynb 
```
