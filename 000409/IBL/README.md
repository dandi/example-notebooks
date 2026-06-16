This notebook provides a comprehensive guide to accessing and analyzing data from the IBL Brain Wide Map dataset (dandiset 000409) in NWB format.

The notebook covers:
- Locating and streaming NWB files from DANDI
- Raw electrophysiology data (AP and LF bands) from Neuropixels probes
- Electrode metadata and anatomical localization (Allen CCFv3 and IBL bregma coordinates)
- Probe anatomy visualization with COSMOS parcellation
- Video data streaming and playback (with nwb-video-widgets)
- Spike sorting results (units table, waveforms, quality metrics)
- Behavioral data: trials, psychometric curves, reaction times
- Wheel position data
- Pose estimation (DeepLabCut) with video overlay
- Passive protocol stimulation data
- Trial-aligned behavioral analysis using pynapple
