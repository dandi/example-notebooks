# DANDI:001828 Example Notebooks

This directory contains example notebooks demonstrating how to access and visualize
the dataset published at [DANDI:001828](https://dandiarchive.org/dandiset/001828).

The dataset comes from the Meletis Lab at Karolinska Institutet and contains fiber
photometry, optogenetics, pose estimation, and behavioral event data across multiple
experimental protocols.

## Notebooks

| Notebook | Protocol                                                        |
|---|-----------------------------------------------------------------|
| `arrow_maze_choice_task.ipynb` | Arrow Maze choice task — pose estimation              |
| `open_field_test.ipynb` | Open Field Test — VAME motif sequences and fiber photometry     |
| `opto_dlight.ipynb` | Optogenetics + dLight — fiber photometry aligned to opto epochs |
| `reaching_test.ipynb` | Reaching Test — reach outcome events and palm kinematics        |
| `water_consumption.ipynb` | Water Consumption — fiber photometry aligned to reach outcomes  |

All notebooks stream NWB files directly from the DANDI archive using the shared
`utils.py` helper.

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001828/MeletisLab
conda env create --file environment.yml
conda activate 001828_demo
```

## Running a notebook

```bash
jupyter notebook arrow_maze_choice_task.ipynb
```
