---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.19.5
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dandi/example-notebooks/blob/master/000108/chunglab/demo/2021-09-27_dandi-demo.ipynb)


## Installing requirements

The cell below installs every Python package needed to run this notebook, at fully pinned versions, using [`uv`](https://github.com/astral-sh/uv) for fast resolution. In Colab the cell is collapsed by default — click the ▶ button to run it.

```python cellView="form"
#@title Installing requirements (click ▶ to run) { display-mode: "form" }
# Colab provides Python 3.13. We install with `uv --system` because Colab's
# kernel runs outside a virtualenv. All versions (direct + transitive) are
# pinned below so the notebook is reproducible regardless of resolver drift.
!pip install -q uv
!uv pip install --system \
    "acres==0.5.0" \
    "aiohappyeyeballs==2.7.1" \
    "aiohttp==3.14.3" \
    "aiosignal==1.4.0" \
    "annotated-types==0.8.0" \
    "arrow==1.4.0" \
    "attrs==26.1.0" \
    "bids-validator-deno==3.0.1" \
    "bidsschematools==1.2.7" \
    "blessed==1.48.0" \
    "bokeh==3.8.2" \
    "certifi==2026.7.22" \
    "cffi==2.1.1" \
    "charset-normalizer==3.4.9" \
    "ci-info==0.4.0" \
    "click==8.4.2" \
    "click-didyoumean==0.3.1" \
    "contourpy==1.3.3" \
    "cryptography==50.0.0" \
    "cycler==0.12.1" \
    "dandi==0.77.0" \
    "dandischema==0.14.0" \
    "deno==2.9.5" \
    "dnspython==2.8.0" \
    "donfig==0.8.1.post1" \
    "email-validator==2.3.0" \
    "etelemetry==0.3.1" \
    "fasteners==0.20" \
    "fonttools==4.63.0" \
    "fqdn==1.5.1" \
    "frozenlist==1.8.0" \
    "fscacher==0.4.4" \
    "fsspec==2025.3.0" \
    "google-crc32c==1.8.0" \
    "h5py==3.16.0" \
    "hdmf==6.2.0" \
    "humanize==4.16.0" \
    "idna==3.18" \
    "imageio==2.37.4" \
    "interleave==0.3.0" \
    "isodate==0.7.2" \
    "isoduration==20.11.0" \
    "jaraco-classes==3.4.0" \
    "jaraco-context==6.1.2" \
    "jaraco-functools==4.6.0" \
    "jeepney==0.9.0" \
    "jinja2==3.1.6" \
    "jinxed==2.1.0" \
    "joblib==1.5.3" \
    "jsonpointer==3.1.1" \
    "jsonschema==4.26.0" \
    "jsonschema-specifications==2025.9.1" \
    "keyring==25.7.0" \
    "keyrings-alt==5.0.2" \
    "kiwisolver==1.5.0" \
    "lazy-loader==0.5" \
    "markupsafe==3.0.3" \
    "matplotlib==3.10.0" \
    "ml-dtypes==0.6.0" \
    "more-itertools==10.8.0" \
    "multidict==6.7.1" \
    "narwhals==2.24.0" \
    "natsort==8.4.0" \
    "networkx==3.6.1" \
    "numcodecs==0.16.5" \
    "numpy==2.1.3" \
    "nwbinspector==0.7.2" \
    "packaging==26.3" \
    "pandas==2.2.3" \
    "pillow==11.3.0" \
    "platformdirs==4.11.3" \
    "propcache==0.5.2" \
    "pycparser==3.0" \
    "pycryptodomex==3.23.0" \
    "pydantic==2.13.4" \
    "pydantic-core==2.46.4" \
    "pydantic-settings==2.15.0" \
    "pynwb==4.1.0" \
    "pyout==0.8.1" \
    "pyparsing==3.3.2" \
    "python-dateutil==2.9.0.post0" \
    "python-dotenv==1.2.3" \
    "pytz==2025.2" \
    "pyyaml==6.0.3" \
    "referencing==0.37.0" \
    "requests==2.32.4" \
    "rfc3339-validator==0.1.4" \
    "rfc3987==1.3.8" \
    "rpds-py==2026.6.3" \
    "ruamel-yaml==0.19.1" \
    "scikit-image==0.25.2" \
    "scipy==1.16.3" \
    "seaborn==0.13.2" \
    "secretstorage==3.5.0" \
    "semantic-version==2.10.0" \
    "six==1.17.0" \
    "tenacity==9.1.4" \
    "tensorstore==0.1.85" \
    "tifffile==2026.8.16" \
    "tornado==6.5.7" \
    "tqdm==4.67.3" \
    "typing-extensions==4.16.0" \
    "typing-inspection==0.4.4" \
    "tzdata==2026.3" \
    "uri-template==1.3.0" \
    "urllib3==2.5.0" \
    "wcwidth==0.8.2" \
    "webcolors==25.10.0" \
    "xyzservices==2026.3.0" \
    "yarl==1.24.5" \
    "zarr==3.1.5" \
    "zarr-checksum==0.4.7"
```

> **⚠️ Restart runtime after install**
>
> The install may upgrade packages already loaded in the kernel. Go to **Runtime → Restart session**, then **Run all cells below** (skip this install cell on re-run).


# Reading volumes from the Chung lab dataset (Dandiset 000108)

This notebook shows how to read image volumes from the Kwanghun Chung lab's
[Dandiset 000108](https://dandiarchive.org/dandiset/000108). The dataset is a whole human
brain cut into roughly 2 mm sections (slabs), each imaged on a light sheet microscope with a
nuclear stain (YO), a stain for NeuN (NN), and a stain for blood vessels (LEC).

The microscope acquires a slab as a series of overlapping stacks, called chunks, that tile
the slab along one axis. Reading a region of a slab therefore means finding the chunks that
cover it, reading from each, and blending them where they overlap. That is what this notebook
does, and it ends with a small blood vessel segmentation on the LEC channel.

The data are stored as [OME-Zarr](https://ngff.openmicroscopy.org/latest/), one Zarr store per
chunk, under each session's `micr/` directory. Each store holds a resolution pyramid, so an
overview of a whole slab can be read at a coarse level in a second or two while the full
resolution data stay available for detailed work. Nothing is downloaded in bulk: every read in
this notebook streams only the blocks it needs, directly from the archive.

```python
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import requests
import zarr
from dandi.dandiapi import DandiAPIClient
from PIL import Image

DANDISET = "000108"
SUBJECT = "MITU01"
SAMPLE = "41"
```

## Finding the chunks of one slab

Assets are named with BIDS-style key-value pairs, so a glob picks out the chunks belonging to
one sample and stain:

```
sub-MITU01/ses-.../micr/sub-MITU01_ses-..._sample-41_stain-YO_run-1_chunk-3_SPIM.ome.zarr
```

`get_assets_by_glob` returns those assets, and `get_content_url` gives an S3 URL that Zarr can
open directly.

```python
def read_pyramid(url):
    """Return one entry per resolution level, with its array, voxel size and origin.

    Voxel size and position come from the OME-NGFF `coordinateTransformations` of each
    level. The axes are (t, c, z, y, x) and only the spatial three matter here. A level
    that carries no transform of its own inherits the voxel size implied by its shape.
    """
    group = zarr.open_group(url, mode="r")
    levels = []
    base_scale = base_shape = None
    for dataset in group.attrs["multiscales"][0]["datasets"]:
        array = group[dataset["path"]]
        shape = np.array(array.shape[2:])
        transforms = dataset.get("coordinateTransformations", [])
        scale = next((np.array(t["scale"][2:], float)
                      for t in transforms if t["type"] == "scale"), None)
        origin = next((np.array(t["translation"][2:], float)
                       for t in transforms if t["type"] == "translation"), None)
        if scale is not None and base_scale is None:
            base_scale, base_shape = scale, shape
        if scale is None and base_scale is not None:
            scale = base_scale * base_shape / shape
        levels.append({"array": array, "shape": shape, "scale": scale,
                       "origin": np.zeros(3) if origin is None else origin})
    return levels


def find_chunks(sample, stain, subject=SUBJECT, dandiset=DANDISET):
    """Every chunk of one (sample, stain), ordered along the tiling axis."""
    with DandiAPIClient() as client:
        assets = client.get_dandiset(dandiset, "draft").get_assets_by_glob(
            f"*sub-{subject}*_sample-{sample}_stain-{stain}_*SPIM.ome.zarr")
        chunks = [{"chunk": int(a.path.split("_chunk-")[1].split("_")[0]),
                   "path": a.path,
                   "url": a.get_content_url(regex="s3")} for a in assets]
    if not chunks:
        raise LookupError(f"no chunks found for sample-{sample} stain-{stain}")
    for rec in chunks:
        rec["levels"] = read_pyramid(rec["url"])
    return sorted(chunks, key=lambda r: r["levels"][0]["origin"][1])


chunks_YO = find_chunks(SAMPLE, "YO")
print(f"{len(chunks_YO)} chunks for sample-{SAMPLE} stain-YO")
print(chunks_YO[0]["path"])
```

## How the chunks are laid out

Each chunk stores its voxel size and its position in the microscope's coordinate frame, both
in micrometers. Printing them shows the tiling: the chunks sit at the same z and x, and step
along y by less than their own width, so consecutive chunks overlap.

```python
level0 = [rec["levels"][0] for rec in chunks_YO]
scale = level0[0]["scale"]
print(f"voxel size (z, y, x): {tuple(float(v) for v in scale)} um")
print(f"chunk shape (z, y, x): {tuple(int(v) for v in level0[0]['shape'])} voxels\n")
print(f"{'chunk':>5} {'y origin (um)':>14} {'y extent (um)':>28}")
for rec, lev in zip(chunks_YO, level0):
    y0 = lev["origin"][1]
    print(f"{rec['chunk']:>5} {y0:>14.1f} {y0:>14.1f} to {y0 + lev['shape'][1] * lev['scale'][1]:>10.1f}")

steps = np.diff([lev["origin"][1] for lev in level0])
overlap_um = level0[0]["shape"][1] * scale[1] - steps.min()
print(f"\nchunks step {steps.min():.0f} um along y and overlap by "
      f"{overlap_um:.0f} um ({overlap_um / scale[1]:.0f} voxels)")
```

## The resolution pyramid

Every chunk holds the same volume at a series of resolutions, each one a factor of two coarser
than the last. Level 0 is the acquired data and level 6 is 64 times smaller along each axis,
which is what makes a whole-slab overview cheap to read.

```python
print(f"{'level':>5} {'shape (z, y, x)':>22} {'voxel size (um)':>28}")
for i, lev in enumerate(chunks_YO[0]["levels"]):
    print(f"{i:>5} {str(tuple(int(v) for v in lev['shape'])):>22} "
          f"{str(tuple(round(float(v), 3) for v in lev['scale'])):>28}")
```

## Stitching chunks into one image

To read a region of the slab we take every chunk that covers it, read the overlapping part of
each, and combine them. In the overlap between two neighbours both chunks have valid data, and
simply preferring one produces a visible seam, because the light sheet illuminates the edges of
a chunk less evenly than its middle. Instead each chunk is given a weight that falls smoothly
to zero over its overlapping margin (a raised cosine), and the result is the weighted average.
The two weights sum to one across the overlap, so the transition is gradual.

Coordinates below are in micrometers within the slab, with the origin at the first chunk. To
go from a voxel index to micrometers, multiply by the voxel size printed above.

```python
def blend_weights(n, overlap):
    """A raised-cosine ramp rising over the first `overlap` voxels and falling over the last."""
    weights = np.ones(n)
    ramp_length = int(min(max(overlap, 0), n // 2))
    if ramp_length > 1:
        ramp = 0.5 * (1 - np.cos(np.pi * (np.arange(ramp_length) + 0.5) / ramp_length))
        weights[:ramp_length] = ramp
        weights[n - ramp_length:] = ramp[::-1]
    return weights


def mosaic_offsets(chunks, level):
    """Chunk positions along y, in micrometers from the start of the slab."""
    origins = np.array([rec["levels"][level]["origin"][1] for rec in chunks])
    return origins - origins.min()


def mosaic_shape(chunks, level):
    """Size of the whole stitched slab at this level, in micrometers."""
    lev = chunks[0]["levels"][level]
    offsets = mosaic_offsets(chunks, level)
    return np.array([lev["shape"][0] * lev["scale"][0],
                     offsets.max() + lev["shape"][1] * lev["scale"][1],
                     lev["shape"][2] * lev["scale"][2]])


def micrometer_extent(lo, image, scale):
    """imshow extent for a y-x image, so a micrometer is the same length on both axes.

    The voxels are not cubic (3.625 um along y against 2.564 um along x), so an
    image drawn on its voxel grid is stretched by about 1.4 along x. Passing this
    extent puts both axes in micrometers and lets the default aspect keep them
    equal.
    """
    return [lo[2], lo[2] + image.shape[1] * scale[2],
            lo[1] + image.shape[0] * scale[1], lo[1]]


def read_mosaic(chunks, lo, hi, level=0, blend=True):
    """Read the box from `lo` to `hi` (z, y, x in micrometers), stitching every chunk in it."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    scale = chunks[0]["levels"][level]["scale"]
    offsets = mosaic_offsets(chunks, level)
    shape = np.maximum(np.round((hi - lo) / scale).astype(int), 1)
    overlap = chunks[0]["levels"][level]["shape"][1] - np.diff(np.sort(offsets)).min() / scale[1] \
        if len(chunks) > 1 else 0

    total = np.zeros(shape, np.float32)
    weight = np.zeros(shape, np.float32)
    for rec, y_offset in zip(chunks, offsets):
        lev = rec["levels"][level]
        origin = np.array([0.0, y_offset, 0.0])
        start = np.maximum(np.floor((lo - origin) / scale).astype(int), 0)
        stop = np.minimum(np.ceil((hi - origin) / scale).astype(int), lev["shape"])
        if np.any(start >= stop):
            continue
        block = np.asarray(lev["array"][0, 0, start[0]:stop[0], start[1]:stop[1],
                                        start[2]:stop[2]], dtype=np.float32)
        ramp = blend_weights(lev["shape"][1], overlap if blend else 0)[start[1]:stop[1]]

        at = np.round((origin + start * scale - lo) / scale).astype(int)
        dst = tuple(slice(max(a, 0), min(a + n, s)) for a, n, s in zip(at, block.shape, shape))
        if any(d.stop <= d.start for d in dst):
            continue
        src = tuple(slice(d.start - a, d.stop - a) for d, a in zip(dst, at))
        piece = block[src]
        piece_weight = ramp[src[1]][None, :, None]
        total[dst] += piece * piece_weight
        weight[dst] += np.broadcast_to(piece_weight, piece.shape)
    return np.where(weight > 0, total / np.maximum(weight, 1e-6), 0.0)


print("slab size (z, y, x):", np.round(mosaic_shape(chunks_YO, 0)).astype(int), "um")
```

## An overview of the whole slab

At level 6 a single plane through the entire slab is a few hundred pixels across and takes a
couple of seconds to read. The photograph taken of the slab before imaging is stored alongside
the image data, which makes a useful check that the reconstruction matches the tissue.

```python
level = 6
slab = mosaic_shape(chunks_YO, level)
scale6 = chunks_YO[0]["levels"][level]["scale"]

z_um = slab[0] / 2  # a plane through the middle of the slab
overview = read_mosaic(chunks_YO, (z_um, 0, 0), (z_um + scale6[0], slab[1], slab[2]), level=level)[0]
print("overview plane:", overview.shape, "pixels at", np.round(scale6, 1), "um")
```

```python
def photo_of(sample, subject=SUBJECT, dandiset=DANDISET):
    """The photograph of the slab, as an RGB array."""
    with DandiAPIClient() as client:
        assets = list(client.get_dandiset(dandiset, "draft").get_assets_by_glob(
            f"*sub-{subject}*_sample-{sample}_photo.jpg"))
        if not assets:
            return None
        url = assets[0].get_content_url(regex="s3")
    return np.asarray(Image.open(BytesIO(requests.get(url, timeout=120).content)))


photo = photo_of(SAMPLE)

fig, axes = plt.subplots(1, 2, figsize=(14, 7))
axes[0].imshow(overview, cmap="cubehelix", vmax=np.percentile(overview, 99.5),
               extent=micrometer_extent((z_um, 0, 0), overview, scale6))
axes[0].set_title(f"sample-{SAMPLE} stain-YO, level {level}")
axes[0].set_xlabel("x (the scan axis, um)")
axes[0].set_ylabel("y (chunks tile along this axis, um)")
if photo is not None:
    axes[1].imshow(photo[::-1, ::-1])
    axes[1].set_title("photograph of the slab")
axes[1].axis("off")
plt.tight_layout()
```

The bands running across the overview are the chunk boundaries. They come from the light sheet
illuminating the middle of a chunk more strongly than its edges, so the intensity varies within
each chunk rather than across the join. Blending removes the discontinuity at the seam but not
this underlying shading, which would need a flat-field correction.

## Full resolution across a seam

The next cell reads a small region at full resolution that straddles the boundary between the
first two chunks, with and without blending. At this scale the individual nuclei of the YO
stain are visible.

```python
offsets = mosaic_offsets(chunks_YO, 0)
seam_y = offsets[1] + 300.0        # just inside the overlap between chunk 1 and chunk 2
centre_x = 46000.0                 # micrometers along the scan axis, near the middle of the slab
z_plane = mosaic_shape(chunks_YO, 0)[0] / 2

lo = (z_plane, seam_y - 700, centre_x - 500)
hi = (z_plane + scale[0], seam_y + 700, centre_x + 500)
blended = read_mosaic(chunks_YO, lo, hi, level=0, blend=True)[0]
averaged = read_mosaic(chunks_YO, lo, hi, level=0, blend=False)[0]
print("region:", blended.shape, "voxels")
```

```python
fig, axes = plt.subplots(1, 2, figsize=(14, 7), sharex=True, sharey=True)
for ax, img, title in ((axes[0], blended, "cosine blending"),
                       (axes[1], averaged, "plain average")):
    ax.imshow(img, cmap="cubehelix", vmax=np.percentile(blended, 99.5),
              extent=micrometer_extent(lo, img, scale))
    ax.set_title(title)
    ax.set_xlabel("x (um)")
axes[0].set_ylabel("y (um)")
plt.tight_layout()

difference = np.abs(blended - averaged)
print(f"the two differ by at most {difference.max():.0f} counts "
      f"({100 * difference.max() / max(blended.max(), 1):.1f}% of the peak)")
```

## The same comparison across the whole slab

One seam at full resolution shows what blending does locally. Reading the whole slab both
ways shows all eight boundaries at once. The profile below each image averages along the scan
axis, which makes the steps easy to see: without blending the intensity jumps where one chunk
gives way to the next, while the blended profile crosses the same boundaries smoothly. The
slow undulation that survives in both is the illumination falloff within each chunk, which
blending is not meant to correct.

```python
overview_averaged = read_mosaic(chunks_YO, (z_um, 0, 0),
                                (z_um + scale6[0], slab[1], slab[2]),
                                level=level, blend=False)[0]

extent6 = micrometer_extent((z_um, 0, 0), overview, scale6)
y_um = np.arange(overview.shape[0]) * scale6[1]
boundaries = mosaic_offsets(chunks_YO, level)[1:]

fig = plt.figure(figsize=(15, 9))
grid = fig.add_gridspec(2, 2, height_ratios=[2.2, 1], hspace=0.3)
for column, (image, title) in enumerate(((overview, "cosine blending"),
                                         (overview_averaged, "plain average"))):
    ax = fig.add_subplot(grid[0, column])
    ax.imshow(image, cmap="cubehelix", vmax=np.percentile(overview, 99.5), extent=extent6)
    ax.set_title(title)
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")

# Profiles averaged along the scan axis, over a few chunk boundaries. Tissue
# structure dominates the overall shape, so the two are compared side by side:
# the averaged profile steps where one chunk gives way to the next.
window = (y_um > 19000) & (y_um < 42000)
ax = fig.add_subplot(grid[1, :])
ax.plot(y_um[window], overview[window].mean(axis=1), lw=1.2, label="cosine blending")
ax.plot(y_um[window], overview_averaged[window].mean(axis=1), lw=1.2, label="plain average")
for boundary in boundaries:
    if window[np.argmin(np.abs(y_um - boundary))]:
        ax.axvline(boundary, color="salmon", lw=0.8, ls="--", zorder=0)
ax.set_xlabel("y (um), dashed lines mark where a chunk starts")
ax.set_ylabel("mean over x")
ax.legend(loc="upper right")

difference = np.abs(overview - overview_averaged)
print(f"the two overviews differ by at most {difference.max():.0f} counts "
      f"({100 * difference.max() / max(overview.max(), 1):.1f}% of the peak), "
      f"and differ at all only within {100 * (difference > 1).mean():.0f}% of the slab, "
      "which is the overlapping margin")
```

## A caveat on the position metadata

The y positions used above are consistent across the dataset, but the z position, which places
a slab within the whole brain, is not always recorded. In sample 41 the LEC chunks disagree:
some report the slab at 82000 um and others report 0. The stitching in this notebook depends
only on the y positions, so it is unaffected, but code that assembles slabs into a whole brain
should check rather than assume.

```python
chunks_LEC = find_chunks(SAMPLE, "LEC")

for name, chunks in (("YO", chunks_YO), ("LEC", chunks_LEC)):
    z_origins = sorted({float(rec["levels"][0]["origin"][0]) for rec in chunks})
    status = "consistent" if len(z_origins) == 1 else "INCONSISTENT"
    print(f"stain {name:>3}: z origins {z_origins} um  ({status})")
```

## A simple blood vessel segmentation

The LEC channel stains blood vessels. Below we read a block at full resolution, enhance
tube-like structures with a vesselness filter built from the eigenvalues of the Hessian, and
threshold the result. The filter follows the formulation used by
[MeVisLab](https://mevislabdownloads.mevis.de/docs/current/FMEstable/ReleaseMeVis/Documentation/Publish/ModuleReference/Vesselness.html)
and described in [Lamy et al. 2020](https://hal.archives-ouvertes.fr/hal-02544493/file/Lamy_ICPR_2020.pdf).

```python
scale_LEC = chunks_LEC[0]["levels"][0]["scale"]
block_origin = np.array([1000, 1700, 14700]) * scale_LEC   # voxel indices to micrometers
block_size = np.array([64, 200, 200]) * scale_LEC

block_LEC = read_mosaic(chunks_LEC, block_origin, block_origin + block_size, level=0)
print("block:", block_LEC.shape, "voxels,", np.round(block_size).astype(int), "um")
```

```python
from skimage.feature import hessian_matrix, hessian_matrix_eigvals
from skimage.filters import threshold_otsu


def vesselness(eigenvalues, a1=0.5, a2=2):
    """Enhance tube-like structures from the sorted Hessian eigenvalues."""
    flat = eigenvalues[1] >= 0
    tube = (~flat) & (eigenvalues[2] < 0)
    plate = (~flat) & (~tube)
    result = np.zeros_like(eigenvalues[0])
    for mask, a in ((tube, a1), (plate, a2)):
        result[mask] = -eigenvalues[1, mask] * np.exp(
            -np.square(eigenvalues[0, mask]) / (2 * np.square(a * eigenvalues[1, mask])))
    return result


hessian = hessian_matrix(block_LEC, sigma=2, use_gaussian_derivatives=False)
enhanced = vesselness(hessian_matrix_eigvals(hessian))

# The Hessian is unreliable within a few voxels of the block face, where the
# Gaussian derivatives run off the edge of the data, so trim a margin before
# choosing a threshold.
margin = 8
interior = (slice(None), slice(margin, -margin), slice(margin, -margin))
raw, enhanced = block_LEC[interior], enhanced[interior]
segmentation = enhanced > threshold_otsu(enhanced)
print(f"{100 * segmentation.mean():.1f}% of the block is segmented as vessel")
```

```python
plane = raw.shape[0] // 2
fig, axes = plt.subplots(1, 3, figsize=(16, 5.5), sharex=True, sharey=True)
axes[0].imshow(raw[plane], cmap="cubehelix", vmax=np.percentile(raw, 99.5))
axes[0].set_title("LEC channel")
axes[1].imshow(enhanced[plane], cmap="cubehelix")
axes[1].set_title("vesselness")
axes[2].imshow(raw[plane], cmap="gray", vmax=np.percentile(raw, 99.5))
axes[2].imshow(segmentation[plane], alpha=0.35)
axes[2].set_title("segmentation")
plt.tight_layout()
```

## Viewing a slab in neuroglancer

The chunks can also be browsed interactively, without any of the reading code above, by
pointing [neuroglancer](https://neuroglancer-demo.appspot.com/) at the Zarr stores. The cell
below prints a link that loads every chunk of one stain as a single layer; neuroglancer places
the chunks using the same OME-NGFF metadata this notebook read. `neuroglancer-stitched.py`,
next to this notebook, builds richer multi-stain links the same way.

```python
import json
from urllib.parse import quote


def neuroglancer_url(chunks, name="sample"):
    layer = {"type": "image", "name": name, "tab": "rendering",
             "source": [f"zarr://{rec['url']}" for rec in chunks]}
    state = {"dimensions": {"z": [scale[0] * 1e-6, "m"],
                            "y": [scale[1] * 1e-6, "m"],
                            "x": [scale[2] * 1e-6, "m"]},
             "displayDimensions": ["z", "y", "x"],
             "layers": [layer], "layout": "yz",
             "layerListPanel": {"visible": True}}
    return "https://neuroglancer-demo.appspot.com/#!" + quote(json.dumps(state))


from IPython.display import Markdown

url = neuroglancer_url(chunks_YO, name=f"sample-{SAMPLE}-YO")
print(f"{len(url)} character link covering {len(chunks_YO)} chunks")
Markdown(f"[Open sample-{SAMPLE} stain-YO in neuroglancer]({url})")
```

## Where to go next

`dashboard.ipynb` in this directory charts which samples and stains exist across the whole
dandiset, which is a good way to pick another slab to look at. `validate_lev6.ipynb` walks
every chunk and checks its coarsest level, which is how the gaps noted above were found.
