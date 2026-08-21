# DANDI Notebooks

This repository contains example notebooks associated with datasets, conference tools, or more generally notebooks that illustrate the use of data on DANDI. This repository is cloned into the [DANDI JupyterHub environment](https://hub.dandiarchive.org). Please note that you will need to visit https://dandiarchive.org and sign in once to get access to the JupyterHub.

## Submission instructions
To add new notebooks, please send a Pull Request. Submissions should use the following file structure:

```
example-notebooks/
└── <dandiset id>/
    └── <org or lab name>/
        └── <mnemonic for paper or analysis>/
            ├── requirements.in
            ├── README.md
            ├── <analysis 1>.ipynb
            ├── <analysis 2>.ipynb
            ├── ...
            └── <analysis n>.ipynb
```

For example, [000055/bruntonlab/peterson21](./000055/BruntonLab/peterson21)

The `README.md` file should explain the goal of the submission, provide links to relevant scientific publications, and explain the purpose of each notebook file.

The `requirements.in` file lists the notebooks' **direct** Python dependencies,
one per line — the packages the notebooks actually import (e.g. `dandi`,
`pynwb`, `remfile`, `matplotlib`). Do not list transitive dependencies or
export a full freeze of your environment; our tooling compiles the complete
pinned set from this file. After adding it, run

```bash
python .github/scripts/lock_notebook.py <path/to/your-notebook>.ipynb
```

which resolves the pins against Colab's runtime and writes the install cell
and Colab badge into the notebook for you. If a notebook needs a specific
version range (say it was written against an older matplotlib API), express
that as a bound in `requirements.in` (e.g. `matplotlib<3.11`).

> **Note:** notebooks are automatically tested in CI, made runnable in Google
> Colab, and published as self-contained [container
> images](.github/docker/README.md). The site also publishes a machine-readable
> index at <https://notebooks.dandiarchive.org/notebooks.json> (per dandiset:
> notebook paths with GitHub, Colab, and docker links) for other sites to embed. Before opening a PR, see **[Adding a
> notebook: CI, Colab, and the exclusion lists](docs/adding-notebooks.md)**
> for how the CI test works, headless-execution gotchas, and the `.github`
> exclusion lists. (Some older submissions carry an `environment.yml` instead
> of `requirements.in`; new submissions should use `requirements.in`.)

Feel free to reach out on the [DANDI helpdesk](https://github.com/dandi/helpdesk/issues/new/choose) with any questions.

## Useful tools

We use https://app.reviewnb.com/ to provide convenient review of notebook diffs in Pull Requests in GitHub web UI.

To assist in reviewing diff's in notebooks locally we recommend to checkout [nbdime](https://nbdime.readthedocs.io) which provides comparable functionality and integrates well with your local git.
