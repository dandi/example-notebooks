# Guo, Inagaki et al., 2017

### This directory a duplicate of the [DJ-NWB-Guo-Inagaki-2017 repository](https://github.com/datajoint-company/DJ-NWB-Guo-Inagaki-2017) as part of the [DataJoint NWB Showcase](https://github.com/datajoint-company/DataJoint-NWB-showcase). Submit any issues to [DJ-NWB-Guo-Inagaki-2017 repository](https://github.com/datajoint-company/DJ-NWB-Guo-Inagaki-2017).


Data pipeline for Guo, Inagaki et al., 2017 from Svoboda Lab.

Data consists of both extracellular and whole-cell recording at the ALM and thalamus regions. The recordings were performed on mice performing tactile discrimination task with and without unilateral photoinhibition. 

This study revealed the thalamic neurons exhibited selective persistent delay activity that predicted movement direction, which is similar to the anterior lateral motor cortex (ALM). This data pipeline contains the ephys and behavior data, and their corresponding analysis that replicate the figures in the paper.

This project presents a DataJoint pipeline design for the data accompanying the paper
> Zengcai V. Guo, Hidehiko K. Inagaki, Kayvon Daie, Shaul Druckmann, Charles R. Gerfen & Karel Svoboda. "Maintenance of persistent activity in a frontal thalamocortical loop" (2017) Nature

https://dx.doi.org/10.1038/nature22324

The data: https://dx.doi.org/10.6080/K03F4MH (Not available)

## Design DataJoint data pipeline 
This repository contains the **Python 3.7** code of the DataJoint data pipeline design for this dataset, as well as scripts for data ingestions and visualization

## Conversion to NWB 2.0
This repository contains the **Python 3.7** code to convert the DataJoint pipeline into NWB 2.0 format (See https://neurodatawithoutborders.github.io/)
Each NWB file represents one recording session. The conversion script can be found [here](scripts/datajoint_to_nwb.py)

## Demonstration of the data pipeline
Data queries and usages are demonstrated in this [Jupyter Notebook](notebooks/Guo-Inagaki-2017-examples.ipynb), where several figures from the paper are reproduced. 

## Schema Diagram
![ERD of the entire data pipeline](images/all_erd.png)

## Instruction to execute this pipeline

### Download original data 

After cloning this repository, download the original data. Once downloaded, you should find 2 folders containing
 intracellular and extracellular data, `whole_cell_nwb2.0` and `extracellular` respectively.
 
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
        "database.prefix": "gi2017_",
        "extracellular_directory": "/path_to_downloaded_data/extracellular/datafiles",
        "intracellular_directory": "/path_to_downloaded_data/whole_cell_nwb2.0"
    }
}
```

Note: make sure to provide the correct database hostname, username and password.
 Then specify the path to the downloaded data directories for intracellular and extracellular data.

### Ingest data into the pipeline

On a new terminal, navigate to the root of your project directory, then execute the following commands:

```
python scripts/ingest_nwb_extracellular.py
```

```
python scripts/ingest_nwb_wholecell.py
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
