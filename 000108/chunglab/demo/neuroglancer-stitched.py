from dandi.dandiapi import DandiAPIClient
import json
from urllib.parse import quote, unquote
import pandas as pd
import numpy as np

cubehelix_template = """
#uicontrol float brightness slider(min=0.0, max=100.0, default=%f)
void main() {
    float x = clamp(toNormalized(getDataValue()) * brightness, 0.0, 1.0);
    float angle = 2.0 * 3.1415926 * (4.0 / 3.0 + x);
    float amp = x * (1.0 - x) / 2.0;
    vec3 result;
    float cosangle = cos(angle);
    float sinangle = sin(angle);
    result.r = -0.14861 * cosangle + 1.78277 * sinangle;
    result.g = -0.29227 * cosangle + -0.90649 * sinangle;
    result.b = 1.97294 * cosangle;
    result = clamp(x + amp * result, 0.0, 1.0);
    emitRGB(result);
}
"""

cubehelix2_template = """
#uicontrol float brightness slider(min=0.0, max=100.0, default=%f)
void main() {
    float x = clamp(toNormalized(getDataValue()) * brightness, 0.0, 1.0);
    float angle = 2.0 * 3.1415926 * (4.0 / 3.0 + x);
    float amp = x * (1.0 - x) / 2.0;
    vec3 result;
    float cosangle = cos(angle);
    float sinangle = sin(angle);
    result.g = -0.14861 * cosangle + 1.78277 * sinangle;
    result.r = -0.29227 * cosangle + -0.90649 * sinangle;
    result.b = 1.97294 * cosangle;
    result = clamp(x + amp * result, 0.0, 1.0);
    emitRGB(result);
}
"""

cubehelix3_template = """
#uicontrol float brightness slider(min=0.0, max=100.0, default=%f)
void main() {
    float x = clamp(toNormalized(getDataValue()) * brightness, 0.0, 1.0);
    float angle = 2.0 * 3.1415926 * (4.0 / 3.0 + x);
    float amp = x * (1.0 - x) / 2.0;
    vec3 result;
    float cosangle = cos(angle);
    float sinangle = sin(angle);
    result.b = -0.14861 * cosangle + 1.78277 * sinangle;
    result.g = -0.29227 * cosangle + -0.90649 * sinangle;
    result.r = 1.97294 * cosangle;
    result = clamp(x + amp * result, 0.0, 1.0);
    emitRGB(result);
}
"""

cubehelix4_template = """
#uicontrol float brightness slider(min=0.0, max=100.0, default=%f)
void main() {
    float x = clamp(toNormalized(getDataValue()) * brightness, 0.0, 1.0);
    float angle = 2.0 * 3.1415926 * (4.0 / 3.0 + x);
    float amp = x * (1.0 - x) / 2.0;
    vec3 result;
    float cosangle = cos(angle);
    float sinangle = sin(angle);
    result.r = -0.14861 * cosangle + 1.78277 * sinangle;
    result.g = -0.29227 * cosangle + -0.90649 * sinangle;
    result.b = 1.97294 * cosangle;
    result = clamp(x + amp * result, 0.0, 1.0);
    emitRGB(result);
}
"""

cubehelix5_template = """
#uicontrol float brightness slider(min=0.0, max=100.0, default=%f)
void main() {
    float x = clamp(toNormalized(getDataValue()) * brightness, 0.0, 1.0);
    float angle = 2.0 * 3.1415926 * (4.0 / 3.0 + x);
    float amp = x * (1.0 - x) / 2.0;
    vec3 result;
    float cosangle = cos(angle);
    float sinangle = sin(angle);
    result.g = -0.14861 * cosangle + 1.78277 * sinangle;
    result.b = -0.29227 * cosangle + -0.90649 * sinangle;
    result.r = 1.97294 * cosangle;
    result = clamp(x + amp * result, 0.0, 1.0);
    emitRGB(result);
}
"""

cubehelix6_template = """
#uicontrol float brightness slider(min=0.0, max=100.0, default=%f)
void main() {
    float x = clamp(toNormalized(getDataValue()) * brightness, 0.0, 1.0);
    float angle = 2.0 * 3.1415926 * (4.0 / 3.0 + x);
    float amp = x * (1.0 - x) / 2.0;
    vec3 result;
    float cosangle = cos(angle);
    float sinangle = sin(angle);
    result.b = -0.14861 * cosangle + 1.78277 * sinangle;
    result.r = -0.29227 * cosangle + -0.90649 * sinangle;
    result.g = 1.97294 * cosangle;
    result = clamp(x + amp * result, 0.0, 1.0);
    emitRGB(result);
}
"""

colormap = {"LEC": cubehelix_template % 20,
            "YO": cubehelix2_template % 40,
            "NN": cubehelix3_template % 80,
            "CR": cubehelix4_template % 50,
            'calretinin': cubehelix4_template % 50,
            'NPY': cubehelix5_template % 50,
            'npy': cubehelix5_template % 50,
            'IBA1': cubehelix6_template % 50,
            'SST': cubehelix4_template % 50}


def get_data(sub):
    api = DandiAPIClient("https://api.dandiarchive.org/api")
    ds = api.get_dandiset("000108")

    assets = list(ds.get_assets_by_glob(f"*{sub}/*SPIM.ome.zarr"))
    photos = list(ds.get_assets_by_glob(f"*{sub}/*_photo.jpg"))
    df = pd.DataFrame([dict([val.split("-")
                             for val in asset.path.split("/")[-1].split(".")[0].split("_")
                             if "-" in val]) for asset in assets])
    samples = sorted(df['sample'].unique(), key=lambda x: int(x.split("R")[0]))
    samples_w_sessions = sorted([val[0] for val in df.groupby(['sample', 'ses'])], key=lambda x: int(x[0].split("R")[0]))
    return df, ds, samples, photos


def get_photo_url(photos, sample):
    photo_url = [photo.get_content_url(regex='s3') for photo in photos if f'_sample-{sample}_' in photo.path]
    return photo_url[0] if photo_url else None


def get_url(ds, subj, sample, stains):
    layers = []
    for stain in stains:
        zarrs = list(ds.get_assets_by_glob(f"*{subj}/*_sample-{sample}_stain-{stain}_run-1*.ome.zarr"))

        sources = [f"zarr://{val.get_content_url(regex='s3')}"
                  for val in sorted(zarrs, key=lambda x: int(x.path.split("_chunk-")[1].split("_")[0]))]
        # print([val.path for val in sorted(zarrs, key=lambda x: int(x.path.split("_chunk-")[1].split("_")[0]))])
        if len(zarrs):
            val = zarrs[0]
            layer = dict(
                source=sources,
                type="image",
                shader=colormap[stain],
                name=val.path.split("_sample-")[1].split("_")[0] + f'-{stain}' + "-" + f'{len(zarrs)}',
                tab='rendering',
            )
            layers.append(layer)

    ng_url = "https://neuroglancer-demo.appspot.com/"
    ng_str = json.dumps(dict(dimensions={"t":[1,"s"],
                                         "z":[0.000002285,"m"],
                                         "y":[0.0000032309999999999996,"m"],
                                         "x":[0.000002285,"m"]},
                             displayDimensions=["z","y","x"],
                             crossSectionScale=50,
                             projectionScale=500000,
                             layers=layers,
                             showDefaultAnnotations=False,
                             layerListPanel={'visible': True},
                             layout="yz"))
    url = f"{ng_url}#!%s" % quote(ng_str)
    return url


if __name__ == "__main__":
    html = "<html><body>\n"
    html += """<div class="absolute-right">
<img id="image-holder" class="rotate-image" width="400px" alt="">
</div>
<style type="text/css">
.button {
  background-color: #4CAF50; /* Green */
  color: white;
  border: none;
}
.rotate-image {
    -webkit-transform: rotate(90deg) scaleY(-1);
    -moz-transform: rotate(90deg) scaleY(-1);
    -ms-transform: rotate(90deg) scaleY(-1);
    -o-transform: rotate(90deg) scaleY(-1);
    transform: rotate(90deg) scaleY(-1);
}
.absolute-right{
    display: inline-block;
    position: fixed;
    top: 0;
    right: 0;
    z-index: 3;
}
</style>
<script>function showMyImage(src) {
  var img = document.getElementById('image-holder');
  img.src = src;
  console.log(src);
  img.style.display = 'block';
  }
</script>
<br/>\n
"""
    sub = 'sub-MITU01'
    # sub = 'sub-MITU01h3'
    df, ds, samples, photos = get_data(sub)
    noprocess = []
    for sample in samples:
        stains = []
        for group in df[df['sample'] == sample].groupby('stain'):
            if not any((group[1].chunk.value_counts().values > 1).tolist()):
                stains.append(group[0])
        if len(stains) == 0:
            noprocess.append(sample)
            continue
        stain_count = df[df['sample'] == sample].groupby('stain').chunk.count()
        url = get_url(ds, sub, sample, stains)
        sample_val = f'{int(sample):03d}' if 'R' not in sample else sample
        row = f'<a href="{url}" target="_blank">Sample: {sample_val}</a> Stains: {list(stain_count.items())}'
        print(sample, list(stain_count.items()), len(url))
        for ses in df[df['sample'] == sample].ses.unique():
            row += f' Session: <a href="https://dandiarchive.org/dandiset/000108/draft/files?location={sub}%2Fses-{ses}%2Fmicr%2F">{ses}</a>'
        photo_url = get_photo_url(photos, sample)
        if photo_url:
            row += f"""  <btn class="button" onClick="showMyImage('{photo_url}');">Photo</btn>"""
        row += '<br/>\n'
        html += row
    if noprocess:
        html += "Could not process:"
        for val in noprocess:
            html += f" {val}"
        html += "<br/>\n"
    html += "</body></html>\n"

    with open(f"index-{sub}.html", "wt") as fp:
        fp.write(html)
    print('could not process:', noprocess)
