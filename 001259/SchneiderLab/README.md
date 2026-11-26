# Example Sessions for Dandiset 001259

These notebooks accompany [Dandiset 001259](https://dandiarchive.org/dandiset/001259/0.261013.2200), "A shared cortical manifold links sensory error to motor planning" (Zempolich and Schneider, 2026). In the task, mice use real-time auditory feedback to adjust ongoing forelimb movements. Each notebook streams one example session and plots one rewarded and one unrewarded trial.

- `ephys_example_notebook.ipynb` shows a session with operant behavior and concurrent OpenEphys recordings in primary auditory cortex (A1).
- `opto_example_notebook.ipynb` shows a session with operant behavior and concurrent optogenetic stimulation.

`stream_nwbfile.py` is a small helper that both notebooks use to stream an NWB file from the DANDI Archive.

The data were converted to NWB with [schneider-lab-to-nwb](https://github.com/catalystneuro/schneider-lab-to-nwb).
