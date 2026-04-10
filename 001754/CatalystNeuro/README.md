# Three-dimensional spatial selectivity of hippocampal neurons during space flight

This example notebook demonstrates how to access and visualize the dataset published at
[DANDI:001754](https://dandiarchive.org/dandiset/001754).

This dataset contains tetrode recordings of hippocampal CA1 place cells from three rats
during the Neurolab Space Shuttle mission (STS-90, 1998). Rats navigated an "Escher Staircase"
track and a "Magic Carpet" track in both ground (preflight) and microgravity (in-flight)
conditions. The data includes spike-sorted units, animal position, pre-computed rate maps,
and behavioral epoch annotations.

Associated publication: Knierim, McNaughton & Poe (2000) "Three-dimensional spatial selectivity
of hippocampal neurons during space flight." *Nature Neuroscience* 3, 209-210.
[doi:10.1038/72910](https://doi.org/10.1038/72910)

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001754/CatalystNeuro
conda env create --file environment.yml
conda activate 001754_demo
```

## Running the notebook

```bash
jupyter notebook 001754_demo.ipynb
```
