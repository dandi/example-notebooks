# Hires, Gutnisky et al., 2015 - A DataJoint example

### This directory a duplicate of the [DJ-NWB-Hires-Gutnisky-2015 repository](https://github.com/datajoint-company/DJ-NWB-Hires-Gutnisky-2015) as part of the [DataJoint NWB Showcase](https://github.com/datajoint-company/DataJoint-NWB-showcase). Submit any issues to [DJ-NWB-Hires-Gutnisky-2015 repository](https://github.com/datajoint-company/DJ-NWB-Hires-Gutnisky-2015).


This notebook presents data and results associated with the following papers:
>Samuel Andrew Hires, Diego A Gutnisky, Jianing Yu, Daniel H O’Connor, and Karel Svoboda. "Low-noise encoding of active touch by
layer 4 in the somatosensory cortex" (2015) eLife (http://doi.org/10.7554/eLife.06619)

This study investigated the spiking variability of layer 4 (L4) excitatory neurons in the mouse barrel cortex, using intracellular recordings. The recordings were performed during a object locating task, where whisker movements and contacts with object were tracked to the milisecond precision. Spiking patterns in L4 neurons appeared irregular at first, however upon aligning to the fine-scale structure of the behavior, the study revealed that spiking patterns are coupled to the temporal sensory input from object contact, with spike rate increases shortly after touch.

A ***DataJoint*** data pipeline has been constructed for this study, with the presented data ingested into this pipeline. This notebook demonstrates the queries, processing, and reproduction of several figures from the paper. From the pipeline, export capability to NWB 2.0 format is also available.

## About the data

The dataset comprises of membrane potential, and spikes of layer 4 (L4) neurons of the mouse's barrel cortex (around C2 column) during a whisker-based object locating task. The behavior data includes detailed description of the trial structure (e.g. trial timing, trial instruction, trial response, etc.) and a variety of whisker movement related tracking data: whisker position, whisker phase, whisker curvature change, touch times, etc.

Original data shared here: http://crcns.org/data-sets/ssc/ssc-5/about-ssc-5

The data in original MATLAB format (.mat) have been ingested into a DataJoint data pipeline presented below. This notebook demonstrates the queries, processing, and reproduction of several figures from the paper. 

Data are also exported into NWB 2.0 format. 

## Design DataJoint data pipeline 
This repository will contain the Python 3.6+ code of the DataJoint data pipeline design for this dataset, as well as scripts for data ingestions and visualization

## Conversion to NWB 2.0
This repository will contain the Python 3.6+ code to convert the DataJoint pipeline into NWB 2.0 format (See https://neurodatawithoutborders.github.io/)

See NWB export code [here](../scripts/datajoint_to_nwb.py)

## Demonstration of the data pipeline
Data queries and usages are demonstrated in this [Jupyter Notebook](notebooks/Hires-Gutnisky-2015-examples.ipynb), where several figures from the paper are reproduced. 

## Architecture of the data pipeline
![ERD of the entire data pipeline](images/all_erd.png)

## Instruction to execute this pipeline

### Download original data 

After cloning this repository, download the original data. Once downloaded, you should find a data directory
named `data` containing 2 subfolders: `metadata` and `datafiles`. 
 
### Setup "dj_local_conf.json"

`dj_local_conf.json` is a configuration file for DataJoint, which minimally specifies the
 database connection information, as well as several other optional configurations.
 
 Create a new `dj_local_conf.json` at the root of your project directory (where you have this repository cloned),
  with the following format:
 
 ```json
{
    "database.host": "database_hostname",
    "database.user": "your_username_here",
	"database.password": "your_password_here",
    "database.port": 3306,
    "database.reconnect": true,
    "loglevel": "INFO",
    "safemode": true,
    "custom": {
	    "database.prefix": "hg2015_",
        "data_directory": ".../path_to_downloaded_data/data"
    }
}
```

Note: make sure to provide the correct database hostname, username and password.
 Then specify the path to the downloaded data directories (parent of the `metadata` and `datafiles`).

### Ingest data into the pipeline

On a new terminal, navigate to the root of your project directory, then execute the following commands:

```
python scripts/ingestion.py
```

```
python scripts/populate.py
```

### Mission accomplished!
You now have a functional pipeline up and running, with data fully ingested.
 You can explore the data, starting with the provided demo notebook.
 
From your project root, launch ***jupyter notebook***:
```
jupyter notebook
```

### Export to NWB 2.0
Data from this DataJoint pipeline can be exported in NWB 2.0 format using this [datajoint_to_nwb.py](../scripts/datajoint_to_nwb.py) script. 
To perform this export for all ingested data, specify the export location (e.g. `./data/exported_nwb2.0`), execute this command from the project root:

```
python scripts/datajoint_to_nwb.py ./data/exported_nwb2.0
```

