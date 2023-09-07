# Example notebooks

This repository contains example notebooks associated with datasets, conference tools, or more generally notebooks that illustrate the use of data on DANDI. This repository is cloned into the [DANDI JupyterHub environment](https://hub.dandiarchive.org). Please note that you will need to visit https://dandiarchive.org and sign in once to get access to the JupyterHub.

## Submission instructions
To add new notebooks, please send a Pull Request. Submissions should use the following file structure:

```
example-notebooks
└── <dandiset id>/
    └── <org or lab name>/
        └── <mnemonic for paper or analysis>/
            ├── environment.yml
            ├── README.md
            ├── <analysis 1>.ipynb
            ├── <analysis 2>.ipynb
            ├── ...
            └── <analysis n>.ipynb
```

For example, [000055/bruntonlab/peterson21](https://github.com/dandi/example-notebooks/tree/9b1fb88667595a3abcdefda46bbe08e538dcbf0f/000055/BruntonLab/peterson21)

The `README.md` file should explain the goal of the submission, provide links to relevant scientific publications, and explain the purpose of each notebook file.

The `environment.yml` file should define the dependencies of the environment required for the notebooks to be executed. `environment.yml` files are like `requirements.txt` files, but are designed to work with `conda`. To create this file, follow these steps:

1. Create a new environment: `conda create -n <env-name> -python <python-version>`
2. Switch into that environment: `conda activate <env-name>`
3. Use `conda install <pkg>` and `pip install <pkg>` to install the necessary dependencies until the notebook runs through successfully.
4. Confirm that all the notebooks can be run without error.
5. Export the environment: `conda env export > environment.yml`.

See detailed instructions for creating a `environment.yml` file [here](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#sharing-an-environment).


Feel free to reach out on the [DANDI helpdesk](https://github.com/dandi/helpdesk/issues/new/choose) with any questions.
