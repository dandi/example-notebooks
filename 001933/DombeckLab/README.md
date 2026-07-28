# DANDI:001933 — Dombeck Lab Fiber Photometry Notebook

This notebook demonstrates how to access data from
**[DANDI:001933](https://dandiarchive.org/dandiset/001933)**, a dataset of
in vivo fiber photometry recordings of striatal dopamine release in awake,
head-fixed mice expressing the dopamine sensor GRAB-DA3m.

Two intersectional mouse lines targeting distinct dopamine neuron subtypes were
studied: Anxa1-iCre mice (Anxa1+, vulnerable subtype) with fiber photometry in
the dorsal lateral striatum (DLS), and Calb1-Cre mice (Calb1+, resilient subtype)
with fiber photometry in the dorsal medial striatum (DMS). Optogenetic activation
of subtype-specific dopamine neuron cell bodies in the substantia nigra pars
compacta (SNc) was achieved via Cre-dependent ChRmine expression and red-light
(635 nm) stimulation. LRRK2-WT and LRRK2-G2019S knockin mice were compared to
investigate how pathogenic LRRK2 kinase activity affects dopamine synaptic function
in a subtype-specific manner.

> **Authentication required** — DANDI:001933 is currently embargoed.
> A DANDI API key is required to stream data. Set it as an environment variable:
> ```bash
> export DANDI_API_KEY=your_key_here
> ```
> In Colab: add it via the Secrets panel (key icon on the left) under the name
> `DANDI_API_KEY`.

**Reference:** Chen, He et al. (in preparation)

---

## Notebooks

### `001933_demo.ipynb`

Streams a single session (subject 4007, Anxa-LRRK2-G2019S, 2025-08-13) from
DANDI and demonstrates:

1. NWBFile and subject metadata
2. Fiber photometry metadata (`FiberPhotometryTable`, devices, indicator) via
   [ndx-fiber-photometry](https://github.com/catalystneuro/ndx-fiber-photometry)
   and [ndx-ophys-devices](https://github.com/catalystneuro/ndx-ophys-devices)
3. Raw fiber photometry — full session and zoomed with stimulation epochs
4. `CommandedVoltageSeries` — LED switching square wave (data provenance)
5. Raw treadmill voltage (data provenance)
6. Processed fiber photometry — baseline-corrected traces and ΔF/F
7. ΔF/F aligned to a single stimulation onset
8. Treadmill behavior (velocity and acceleration)
9. Optogenetic epochs table — per-epoch power values and full-session power map
10. Optogenetics metadata via [ndx-optogenetics](https://github.com/catalystneuro/ndx-optogenetics)
11. Peri-stimulus ΔF/F (PSTH) — grand average, per-power traces, single-trial heatmap

---

## Installing the dependencies

```bash
git clone https://github.com/dandi/example-notebooks
cd example-notebooks/001933/DombeckLab
conda env create --file environment.yml
conda activate dombeck_lab_001933
```
