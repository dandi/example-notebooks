# 000458 - PSTH Neurosift Exploration

See [001_summarize_contents.ipynb](./001_summarize_contents.ipynb) for a summary of the contents of the NWB files in this Dandiset, including the trial information. You can use that to decide which NWB files to examine. Here's an example of one that targets the motor cortex:

```
Asset 7: sub-551397/sub-551397_ses-20210211_behavior+ecephys.nwb -- size: 15202.44 MB
in vivo electrophysiology in a head-fixed mouse during cortical electrical microstimulation
EEG and Neuropixels recording during wakefulness and isoflurane anesthesia
single pulse electrical stimuli targeted to MOs (deep layers)
  1800 trials
  BEHAVIORAL EPOCHS
    awake: 386 valid and not running
    isoflurane: 480 valid and not running
    recovery: 553 valid and not running
  STIMULUS TYPES
    electrical: 1103 valid and not running
    visual: 316 valid and not running
  STIMULUS DESCRIPTIONS
    biphasic: 1103 valid and not running
    white circle: 316 valid and not running
  ESTIM TARGET REGIONS
    MOs: 1103 valid and not running
    n/a: 316 valid and not running
```

First navigate to this Dandiset on DANDI Archive: [000458](https://dandiarchive.org/dandiset/000458). On the right panel, click on "Files" and then find [subject 551397](https://dandiarchive.org/dandiset/000458/0.230317.0039/files?location=sub-551397&page=1). For that NWB file, click on "OPEN WITH -> Neurosift". That should bring you to that file's [Neurosift homepage](https://neurosift.app/?p=/nwb&url=https://api.dandiarchive.org/api/assets/d966b247-2bac-4ef0-8b80-aae010f50c98/download/&dandisetId=000458&dandisetVersion=0.230317.0039).

* In Neurosift, open the "Intervals" panel and then click "PSTH" for the "trials" table.
* Select "Group trials by: behavioral_epoch" and "Sort units by: location".
* Select "Trials filter" in the bottom right and enter `is_valid === 1 && is_running === 0 && stimulus_type === "electrical"`. This will restrict the trials to those that are valid, not running, and have an electrical stimulus.
* Scroll down on the units table and click to select some units in the MOs region. You can also use the "Select units" link at the bottom to select all MOs units.
* The raster plots show the spike trains for the unit where the Y-axis is the trial number and the X-axis is time aligned to the stimulus onset.
* Unit 500 shows a clear pattern of decreased activity following the stimulus for around 0.15 seconds and then a sharp increase in activity for the "awake" trials.
* Try adjusting the trials filter to have stimulus_type === "visual" instead of "electrical" to see that the pattern is not present for visual stimuli.
* Try selecting units at other locations.
* You can also adjust other settings.
* To share your view, use the "Share this tab" on the left panel of Neurosift. [Here's a link with the predefined state intact](https://neurosift.app/?p=/nwb&url=https://api.dandiarchive.org/api/assets/d966b247-2bac-4ef0-8b80-aae010f50c98/download/&dandisetId=000458&dandisetVersion=0.230317.0039&tab=view:PSTH|/intervals/trials^/units&tab-state=H4sIAAAAAAAAA03SvW7bMBSG4VsxOGRSC%2FE3dgAvGYJk7d%2BSFIYiMRIBiTREKkEQ%2BN77SkGLDt%2Bgw8f00Qd9iOxH3xbf%2FYyhPHRZ3Dyag6zMQRFNDLHEkWuyJ4fK1jWRRBFNDLHEkWuyJziJkziJkziJkziJkziJkziFUziFUziFUziFUziFUziN0ziN0ziN0ziN0ziN0ziDMziDMziDMziDMziDMziLsziLsziLsziLsziLsziHcziHcziHc7g953vOD5zTm6U3S2%2BW3iy9WXqz9Oboy9GVoytXm9%2BVaMbQxx%2FpVzOH5nn0a%2FEil2YupxImLxD9nJbz7ftfIW7Esx%2Ba15DmZjz5c2oHUYnC4Zjvwlj8jAj59MrN3e54PO7k7upqx2ReYgyx32b1Osv8xTIu%2BVTez34bP4ntM5hD24xPgntzmsv6SeT%2FF3gUY2qbElJENLldt3wLsUtv35rY%2B%2B%2BFFT4%2B34JdvtRfLc7HjgcpLpU4z%2F4lb2RYf5K3ncu8%2BGqb3Idc%2Fj1PKZXBd5%2BzF96R4eBDP6xXT74Ly8TlcZluQ%2BROXV8ufwD179KNzQIAAA%3D%3D).

Now you can explore the other NWB files in this Dandiset!