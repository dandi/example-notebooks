# DANDI:001550 — Pagan Lab Behavioral and Optogenetics Notebooks

These notebooks demonstrate how to access data from
**[DANDI:001550](https://dandiarchive.org/dandiset/001550)**, a dataset of
behavioral sessions from Long-Evans rats performing multi-sensory decision-making tasks.
A subset of sessions (TaskSwitch6, 5 subjects) include wireless optogenetics
(Cerebro system, Karpova Lab) used to bilaterally inactivate the Frontal Orienting
Field (FOF) via AAV2/5-mDlx-ChR2-mCherry.

**Reference:** Pagan et al., *Nature* 639, 421–429 (2025).
doi:[10.1038/s41586-024-08433-6](https://doi.org/10.1038/s41586-024-08433-6)

---

## Notebooks

### `01_behavior_demo.ipynb`

Streams a TaskSwitch6 session (subject P100, 2019-04-23) from DANDI and demonstrates:

- Session and subject metadata
- Task vocabulary: event types (port pokes), state types (FSM states), action types (sounds)
- Behavioral recording: events, states, and actions tables
- Visualisations using `ndx_structured_behavior.plot`
- Trials table: scalar columns, stimulus parameters, auditory pulse times
- Pulse-time reference frame (relative to cpoke onset) and conversion to absolute time
- State-transition probability matrix and graph

### `02_optogenetics_demo.ipynb`

Streams a TaskSwitch6 session with active laser stimulation (subject P131, 2019-08-15)
and demonstrates:

- `OptogeneticStimulusSite`, `OptogeneticSeries` step-function laser power (watts) for each hemisphere
- Rich structured metadata via `ndx-optogenetics` 0.3.x: excitation source, optical
  fiber implant locations, viral vector, injection coordinates
- Reconstructing per-trial stimulation intervals
- `OptogeneticEpochsTable`: pulse protocol parameters per epoch

---

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001550/PaganLab
conda env create --file environment.yml
conda activate pagan_lab_001550
```