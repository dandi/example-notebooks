# Streaming and interacting with NWB data from DANDI

This example notebook demonstrates how to stream an NWB file from DANDI and perform analyses with the data using pynapple. This notebook is intended to be used at the NWB and DANDI workshops as an interactive tutorial.

The data used in this tutorial were used in this publication: [Sargolini, et al. "Conjunctive representation of position, direction, and velocity in entorhinal cortex." Science 312.5774 (2006): 758-762](https://www.science.org/doi/10.1126/science.1125572). The data can be found on the DANDI Archive in [Dandiset 000582](https://dandiarchive.org/dandiset/000582).


## Installing the dependencies

To set up the environment on your local computer, run the following commands.

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/tutorials/bcm_2024/
conda env create --file environment.yml
conda activate bcm-workshop
```

## Running the notebook

To open the notebook in jupyter, run the following commands.

```bash
jupyter lab analysis-demo.ipynb
```