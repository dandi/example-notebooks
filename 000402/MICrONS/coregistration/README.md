# MICrONS Co-registration Analysis Notebook
**This is an example notebook on how query functional data from DANDI and update it with co-registration information to analyze structure-function data in one place.**

This project was developed during the 2023 NWB NeuroData ReHack workshop held in Granada, Spain. Please contact us at info@bossdb.org if you have any questions. 

## Why is this needed?
Comparison and generation of functional connectivity networks and structural connectivity networks is a key goal of the MICrONS project and requires joint analysis across archives. This notebook provides a starting point for those who want a configurable and dynamic way of obtaining the latest co-registered functional and structural data.

Our goal with this notebook to provide a seamless integration of  generate novel insight into the stimulus-dependent and time-dependent activation of functional subnetworks. This will also allow direct investigation of causal connectivity estimation using functional data. Follow on work could investigate improvements to functional connectivity estimation methods. Even more exciting, however, is the potential to generate a wide range of hypotheses relating the structure and function of neural networks within mammalian cortex.

## How to run
You'll need a fresh python virtual environment (ver. 3.8 or higher) to run this notebook.

1. Install python requirements from `requirements.txt` or through conda from the `enviornment.yml` file.
2. Run `microns_nwb_coreg_notebook` notebook for a complete end-to-end demo of how to integrate the latest co-registed cells from CAVE with the MICrONS functiondal data stored in DANDI.
3. Feel free to import/modify `microns_nwb_coreg.py` or `ng_utils.py` script functions for your own use-case!

## Citations 
>O. Rübel et al., “The Neurodata Without Borders ecosystem for neurophysiological data science,” eLife, vol. 11, p. e78362, Oct. 2022, doi: 10.7554/eLife.78362.

> J. A. Bae et al., “Functional connectomics spanning multiple areas of mouse visual cortex,” bioRxiv, p. 2021.07.28.454025, Jan. 2021, doi: 10.1101/2021.07.28.454025.

> Z. Ding et al., “Functional connectomics reveals general wiring rule in mouse visual cortex,” Neuroscience, preprint, Mar. 2023. doi: 10.1101/2023.03.13.531369.
