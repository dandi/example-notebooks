# 001075 - Neural signal propagation atlas of Caenorhabditis elegans

## How to cite

Randi, Francesco; Sharma, Anuj; Dvali, Sophie; Leifer, Andrew M. (2024) Neural signal propagation atlas of Caenorhabditis elegans (Version 0.240930.1859) [Data set]. DANDI archive. https://doi.org/10.48324/dandi.001075/0.240930.1859



## Setup

Install [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your machine. 
Install `git` and clone the example notebook repository:

```bash
conda install git
git clone https://github.com/dandi/example-notebooks.git
```

Then create a specific environment for this notebook using:

```bash
conda env create --file example-notebooks/001075/001075_notebook_environment.yml
```

Then activate the environment:

```bash
conda activate leifer_notebooks_created_8_29_2024
```

Finally, start Jupyter:

```bash
jupyter notebook
```

And select the notebook `001075_paper_figure_1d.ipynb` from the file explorer in the browser.

If interested in creating your own plots, refer to the code in `utils_001075` for how to handle the data streams.

Note that all timing information is aligned to the NeuroPAL imaging system.



## Help

- Dataset: https://dandiarchive.org/dandiset/001075/0.240930.1859
- Original publication: [Neural signal propagation atlas of Caenorhabditis elegans](https://www.nature.com/articles/s41586-023-06683-4)
- [Visualize (Neurosift)](https://neurosift.app/?p=/dandiset&dandisetId=001075&dandisetVersion=0.240930.1859)
  - Note: the files are split by 'imaging' (raw) and 'segmentation' (processed). To view both, select a combined 
    view for the same session: [example](https://neurosift.app/?p=/nwb&url=https://api.dandiarchive.org/api/assets/5feda038-0c84-494a-a0e0-c3ef8ec194d1/download/&url=https://api.dandiarchive.org/api/assets/40a6799b-4835-4170-89bb-9a866082e503/download/&dandisetId=001075&dandisetVersion=draft). 
- [NWB file basics](https://pynwb.readthedocs.io/en/stable/tutorials/general/plot_file.html#sphx-glr-tutorials-general-plot-file-py)
- [How to read NWB files](https://pynwb.readthedocs.io/en/stable/tutorials/general/scratch.html#sphx-glr-tutorials-general-scratch-py)
- [Data analysis with NWB files](https://pynwb.readthedocs.io/en/stable/tutorials/general/scratch.html#sphx-glr-tutorials-general-scratch-py)
