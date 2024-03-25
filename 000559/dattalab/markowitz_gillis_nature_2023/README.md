# Figure Reproductions for Dandiset 000559

This submission provides three figure reproductions for the Dandiset 000559, which corresponds to the 2023 Nature paper: [Spontaneous behavior is structured by reinforcement without explicit reward](https://doi.org/10.1038/s41586-022-05611-2) by Markowitz et al.

Each notebook provides an example of how to access the critical data and metadata from the three types of experiments in the dataset:

- `reproduce_figure1d.ipynb` demonstrates how the behavioral kinematic variables (position, velocity, etc.), along with the fluorescence traces, are stored for the reinforcement photometry experiments
- `reproduce_figure_S1.ipynb` shows how the fluorescence images for the _in vitro_ experiments are stored
- `reproduce_figure_S3.ipynb` displays how are the keypoint data, along with associated fluorescence traces, are stored for the keypoint tracking experiments

Note: `reproduce_figure1d.ipynb` and `reproduce_figure_S1.ipynb` use the conda environment defined by the 
`environment.yaml` file, but `reproduce_figure_S3.ipynb` uses a different environment defined by the 
`environment_S3.yaml` due to dependency conflicts.