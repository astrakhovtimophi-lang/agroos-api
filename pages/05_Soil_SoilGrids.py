import streamlit as st
from styles import apply_styles

apply_styles()

import json
from pathlib import Path
import requests
import numpy as np
import pandas as pd
import tifffile
from io import BytesIO
from shapely.geometry import shape

st.title("Soil (SoilGrids)")

FIELDS_FILE = Path("data") / "fields.geojson"

def load_fields():
    if FIELDS_FILE.exists():
        fc = json.loads(FIELDS_FILE.read_text())
        return fc.get("features", [])
    return []

def centroid(geom):
    poly = shape(geom)
    c = poly.centroid
    return c.y, c.x

def read_tiff_mean(data):
    arr = tifffile.imread(BytesIO(data)).astype("float32")
    arr[arr < -10000] = np.nan
    return float(np.nanmean(arr))

fields = load_fields()

if not fields:
    st.warning("Нет сохранённых полей. Сначала создай поле в Field Manager.")
    st.stop()

names = []
geoms = []

for f in fields:
    names.append(f["properties"].get("name","field"))
    geoms.append(f["geometry"])

choice = st.selectbox("Поле", names)
geom = geoms[names.index(choice)]

lat,lon = centroid(geom)

st.write("Центр поля:",lat,lon)

layers = {
"pH":"phh2o_0-5cm_mean",
"SOC":"soc_0-5cm_mean",
"Clay":"clay_0-5cm_mean"
}

WCS="https://maps.isric.org/mapserv?map=/map/soilgrids.map"

def fetch(layer):

    eps=0.00001

    params=[
("service","WCS"),
("version","2.0.1"),
("request","GetCoverage"),
("coverageId",layer),
("format","image/tiff"),
("subset",f"Long({lon-eps},{lon+eps})"),
("subset",f"Lat({lat-eps},{lat+eps})")
]

    r=requests.get(WCS,params=params)
    r.raise_for_status()

    return read_tiff_mean(r.content)

if st.button("Fetch soil data"):

    rows=[]

    for k,v in layers.items():

        try:
            val=fetch(v)
        except Exception as e:
            val=None

        rows.append({
        "Layer":k,
        "Value":val
        })

    df=pd.DataFrame(rows)

    st.dataframe(df)

    ph=df[df["Layer"]=="pH"]["Value"].iloc[0]

    if ph:
        if ph<5.5:
            st.warning("Кислая почва — возможно нужно известкование")
        elif ph>7.5:
            st.info("Щелочная почва")
        else:
            st.success("pH в норме")

