# Figure 2: peri-head distance coding in the mouse brainstem

Reproduces the Figure 2 panels of Xiao, Severson, et al. (2026),
*Peri-Head Distance Coding in the Mouse Brainstem*, from
[Dandiset 001687](https://dandiarchive.org/dandiset/001687).

The notebook streams six processed session files with `remfile`, so it never
downloads a whole asset, and draws three panels per unit:

- **Rasters** aligned to wall-pass onset, coloured by wall distance
- **PETHs** recomputed from spike times, one trace per distance, mean +/- SEM
- **Tuning curves** read from `processing/wall_tuning`

The six example units span the three response classes described in the paper:
one *proximity* unit whose firing rises monotonically as the wall nears, four
*map* units tuned to a preferred distance, and one *suppressed* unit.

## Data

| | |
|---|---|
| Dandiset | [001687](https://dandiarchive.org/dandiset/001687) |
| Version | `0.260805.1529` (pinned, so the figure is reproducible) |
| Assets read | 6 processed NWB files, ~7 MB each |

Each session also has a companion raw asset (`_ecephys+image`) carrying the
30 kHz broadband, 1 kHz LFP, digital TTLs and the behaviour video. The notebook
does not need those.

## Related

- Manuscript code: <https://github.com/wanglab-neuro/2026_Xiao-Severson_Peri-head-distance>
