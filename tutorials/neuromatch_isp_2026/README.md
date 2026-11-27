# Neuromatch Impact Scholars Program workshop (2026)

Materials for the DANDI + NWB workshop given to the Neuromatch Impact Scholars Program on 30 November 2026.

The workshop is an entry-level, hands-on introduction to finding open neurophysiology data on the DANDI Archive, streaming it without downloading whole datasets, and analyzing NWB files in Python. It assumes Python and Colab experience and no prior knowledge of NWB or DANDI.

### Notebooks

- `00_setup_check.ipynb`: a 5-minute check to run before the workshop. It installs the packages, streams one file and reports how long that took.
- `workshop.ipynb`: the workshop itself, in three parts.
  - **Part A. Find**: search Dandisets from Python and read their metadata.
  - **Part B. Stream**: open one session of the IBL Brain Wide Map ([DANDI:000409](https://dandiarchive.org/dandiset/000409)) and plot a psychometric curve from the trials table.
  - **Part C. Analyze**: align one motor cortex unit's spikes to stimulus and movement onset, then open an Allen Institute calcium imaging file ([DANDI:000728](https://dandiarchive.org/dandiset/000728)) with the same code.
- `workshop_solutions.ipynb`: an instructor copy of the workshop with every blank filled in.

Each part starts with a catch-up cell and ends with a checkpoint, so the notebook can be followed live in a large group. Exercises are fill-in-the-blank: most of the code is given, and participants replace each `___` with the missing piece. Each exercise has a hidden solution right below it.

### Design

Same philosophy as the [quick start tutorial](../open_data_quick_start_2026): short sentences, short code cells, static plots only, readable when screen-shared.
