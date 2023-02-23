This folder contains notebooks that demonstrate how to work with data in dandiset 000039.

Create_manifest.ipynb creates a manifest documenting some of the metadata of each asset. This creates a dataframe that provides the transgenic line of the mouse recorded in each session, the area that was imaged, the date of acquisition, and the id, age, and sex of the mouse. 

Contrast_analysis.ipynb demonstrates how to read data from an individual asset and computes tuning curves for individual neurons, showing their average response to the stimulus direction X contrast. This type of analysis was used in Millman et al 2020 (https://elifesciences.org/articles/55130). This notebook copies some functions from https://github.com/AllenInstitute/Contrast_Analysis.

Environment.yml documents the environment of dandihub when these notebooks were made. It likely contains many modules that are unnecessary to run these notebooks.

