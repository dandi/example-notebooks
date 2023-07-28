# Chen et al., 2017

This repository sets up the data pipeline corresponding to the data from Chen et al., (2017). **"A Map of Anticipatory Activity in Mouse Motor Cortex."** and provides a Jupyter Notebook demonstrating the use of the DataJoint pipeline in replicating some of the main figures.

Link to the publication: http://dx.doi.org/10.1016/j.neuron.2017.05.005

Link to the original data (need to ask for permission): https://www.dropbox.com/sh/i5kqq99wq4qbr5o/AABagZ8a9uIiZKxrw9MK7OYIa/nwb2/tsai_wen_nwb2?dl=0&subfolder_nav_tracking=1

Link to the exported nwb files: https://drive.google.com/drive/u/1/folders/18AQl-FIVIdgRWzEFb5BVNxeGuiyrnT0c

Access to view the notebook: https://github.com/vathes/Chen-2017/blob/master/notebooks/Chen-2017-examples.ipynb

This study characterized selectivity of cells in anterior lateral motor cortex (ALM) and medial motor cortex (MM). Cells are classified into 5 types: lick direction cells (lick), object location cells (lick), outcome cells (outcome), complex selective cells that are selective to multiple features, and non selective cells. The notebook in this repository replicates Figure 4, 5 and part of Figure 6 of the paper.

## Schema structure

The `lab` schema:

![lab schema](images/lab.png)

The `experiment` schema:

![experiment schema](images/experiment.png)

The `imaging` schema:

![imaging schema](images/imaging.png)


## Instrunctions on getting the pipeline and notebook up and running locally.

1. This repo comes with a set up for [Docker](https://www.docker.com). To take advantage, be sure to install `docker` and `docker-compose`.

2. Set up your local mysql server.

3. `git clone https://github.com/vathes/Chen-2017.git`

4. Inside the repository, create/open a file called `.env` and paste in the following content, being sure to replace `YOUR_USER_NAME` and `YOUR_PASSWORD` with your actual database username and password, respectively.
    ```
    DJ_HOST=host.docker.internal
    DJ_USER=YOUR_USER_NAME
    DJ_PASS=YOUR_PASSWORD
    ```
5. Create a directory called `data`, and download the data from the link https://www.dropbox.com/sh/i5kqq99wq4qbr5o/AABagZ8a9uIiZKxrw9MK7OYIa/nwb2/tsai_wen_nwb2?dl=0&subfolder_nav_tracking=1. Make sure that the downloaded NWB files (ending with `.nwb`) are found inside the directory `data`.

6. Run the bash script with command `bash chen2017.sh` to trigger the ingestion of the data from NWB into the DataJoint pipeline.
    The whole script takes a few hours to run. After it's done, you will find the NWB files in the directory `data/NWB 2.0`

7. To run the notebook, open your browser and navigate to http://localhost:8820/notebooks/Chen-2017-examples.ipynb
