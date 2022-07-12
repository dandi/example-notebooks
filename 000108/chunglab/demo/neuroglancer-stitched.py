from dandi.dandiapi import DandiAPIClient
import json
from urllib.parse import quote, unquote
import pandas as pd

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
colormap = {"LEC": 10, "YO": 40, "NN": 80}

api = DandiAPIClient("https://api.dandiarchive.org/api")
ds = api.get_dandiset("000108")

assets = list(ds.get_assets_by_glob(f"*sub-MITU01/*SPIM.ome.zarr"))
photos = list(ds.get_assets_by_glob(f"*sub-MITU01/*_photo.jpg"))
df = pd.DataFrame([dict([val.split("-")
                         for val in asset.path.split("/")[-1].split(".")[0].split("_")
                         if "-" in val]) for asset in assets])
samples = sorted(df['sample'].unique(), key=lambda x: int(x.split("R")[0]))
samples_w_sessions = sorted([val[0] for val in df.groupby(['sample', 'ses'])], key=lambda x: int(x[0].split("R")[0]))


def get_photo_url(photos, sample):
    photo_url = [photo.get_content_url(regex='s3') for photo in photos if f'_sample-{sample}_' in photo.path]
    return photo_url[0] if photo_url else None


def get_url(ds, sample, ses, stain):
    zarrs = list(ds.get_assets_by_glob(f"*sub-MITU01/*_ses-{ses}*_sample-{sample}_stain-{stain}_run-1*.ome.zarr"))

    #print([a.path for a in zarrs])
    layers = []
    for val in sorted(zarrs, key=lambda x: int(x.path.split("_chunk-")[1].split("_")[0])):
        layer = dict(
                source=f"zarr://{val.get_content_url(regex='s3')}",
                type="image",
                shader=cubehelix_template % (colormap[stain] if stain in colormap else 40),
                name=val.path.split("_sample-")[1].split("_")[0] + "-" + f'{int(val.path.split("_chunk-")[1].split("_")[0]):02d}'
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
                             layout="yz"))
    url = f"{ng_url}#!%s" % quote(ng_str)
    return url, len(zarrs)


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
    for sample, ses in samples_w_sessions:
        stains = df[df['sample'] == sample].stain.unique()
        row = f"{sample}: "
        for stain in stains:
            print(sample, ses, stain)
            url, nchunks = get_url(ds, sample, ses, stain)
            row += f'<a href="{url}" target="_blank">{stain}+{nchunks}</a> '
        row += f' - <a href="https://dandiarchive.org/dandiset/000108/draft/files?location=sub-MITU01%2Fses-{ses}%2Fmicr%2F">{ses}</a>'
        photo_url = get_photo_url(photos, sample)
        if photo_url:
            row += f""" <btn class="button" onClick="showMyImage('{photo_url}');">Photo</btn>"""
        row += '<br/>\n'
        html += row
    html += "</body></html>\n"

    with open("index.html", "wt") as fp:
        fp.write(html)
