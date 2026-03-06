import streamlit as st
from i18n import tr
from styles import apply_styles

apply_styles()

import json
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import tifffile
from io import BytesIO
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pystac_client import Client
from pyproj import Transformer

try:
    import rasterio
    from rasterio.mask import mask
except Exception as e:
    st.error("rasterio missing/broken. For Yield page we need it for NDVI crop. Run pip install -r requirements.txt")
    st.stop()

st.title(tr("module_yield_prediction"))
st.caption("Простой прогноз: NDVI (сцена) + почва (SoilGrids) + погода (Open-Meteo). Это НЕ точный агросервис, но даёт полезный ориентир.")

FIELDS_FILE = Path("data") / "fields.geojson"
if not FIELDS_FILE.exists():
    st.error("Нет data/fields.geojson. Сначала сохрани поле в Field Manager.")
    st.stop()

fc = json.loads(FIELDS_FILE.read_text(encoding="utf-8"))
features = fc.get("features", [])
if not features:
    st.error("В fields.geojson нет полей. Сохрани поле в Field Manager.")
    st.stop()

names, geoms = [], []
for f in features:
    g = f.get("geometry")
    if not g: 
        continue
    nm = (f.get("properties", {}) or {}).get("name") or "field"
    names.append(nm)
    geoms.append(g)

choice = st.selectbox("Saved field", names, key="yield_field")
geom = geoms[names.index(choice)]
poly = shape(geom)
cent = poly.centroid
lat, lon = float(cent.y), float(cent.x)
st.write(f"Centroid: lat={lat:.6f}, lon={lon:.6f}")

c1, c2, c3 = st.columns(3)
with c1:
    start = st.date_input("NDVI start", value=date.today() - timedelta(days=60), key="yield_start")
with c2:
    end = st.date_input("NDVI end", value=date.today() - timedelta(days=1), key="yield_end")
with c3:
    max_cloud = st.slider("Max cloud (%)", 0, 90, 50, key="yield_cloud")

crop = st.selectbox("Crop (template)", ["Wheat", "Corn", "Sunflower", "Soy"], key="yield_crop")

# SoilGrids WCS (point tiny bbox)
WCS = "https://maps.isric.org/mapserv?map=/map/soilgrids.map"

def read_tiff_mean(tiff_bytes: bytes):
    arr = tifffile.imread(BytesIO(tiff_bytes)).astype("float32")
    arr[arr < -10000] = np.nan
    return float(np.nanmean(arr))

def soil_point(cov_id: str, lat: float, lon: float):
    eps = 0.00001
    params = [
        ("service","WCS"),
        ("version","2.0.1"),
        ("request","GetCoverage"),
        ("coverageId", cov_id),
        ("format","image/tiff"),
        ("subset", f"Long({lon-eps},{lon+eps})"),
        ("subset", f"Lat({lat-eps},{lat+eps})"),
    ]
    r = requests.get(WCS, params=params, timeout=25)
    r.raise_for_status()
    return read_tiff_mean(r.content)

def pick_asset(item, candidates):
    keys = list(item.assets.keys())
    for c in candidates:
        if c in item.assets:
            return c
    for c in candidates:
        for k in keys:
            if c.lower() in k.lower():
                return k
    return None

def read_clip(url: str, poly_wgs84):
    with rasterio.open(url) as src:
        if src.crs is None:
            raise ValueError("Raster has no CRS")
        if "4326" in str(src.crs):
            poly_src = poly_wgs84
        else:
            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            poly_src = transform(lambda x, y, z=None: transformer.transform(x, y), poly_wgs84)
        out_img, _ = mask(src, [mapping(poly_src)], crop=True)
        arr = out_img[0].astype("float32")
        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan
        return arr

def weather_7d(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "auto"
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    d = r.json().get("daily", {})
    rain = d.get("precipitation_sum", [])[:7]
    tmax = d.get("temperature_2m_max", [])[:7]
    return float(np.nansum(rain)) if rain else 0.0, float(np.nanmean(tmax)) if tmax else np.nan

if st.button("Run prediction", key="yield_run"):
    # 1) NDVI mean (best scene in range)
    with st.spinner("Searching Sentinel-2 scenes..."):
        catalog = Client.open("https://earth-search.aws.element84.com/v1")
        dt = f"{start.isoformat()}/{end.isoformat()}"
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            intersects=geom,
            datetime=dt,
            query={"eo:cloud_cover":{"lt": max_cloud}},
            limit=150
        )
        items = list(search.items())

    if not items:
        st.error("No Sentinel-2 scenes found. Try wider date range or higher cloud.")
        st.stop()

    items.sort(key=lambda it: (it.properties.get("eo:cloud_cover", 9999), it.properties.get("datetime","")))
    item = items[0]

    red_key = pick_asset(item, ["B04","red","SR_B4","band_4"])
    nir_key = pick_asset(item, ["B08","nir","SR_B8","band_8","B8A"])
    if red_key is None or nir_key is None:
        st.error("RED/NIR assets not found.")
        st.stop()

    with st.spinner("Downloading bands + computing NDVI..."):
        red = read_clip(item.assets[red_key].href, poly)
        nir = read_clip(item.assets[nir_key].href, poly)
        ndvi = (nir - red) / (nir + red + 1e-6)
        ndvi = np.clip(ndvi, -1, 1)
        ndvi_mean = float(np.nanmean(ndvi))

    # 2) Soil point values
    with st.spinner("Fetching soil (SoilGrids)..."):
        try:
            ph = soil_point("phh2o_0-5cm_mean", lat, lon)
        except:
            ph = np.nan
        try:
            soc = soil_point("soc_0-5cm_mean", lat, lon)  # g/kg
        except:
            soc = np.nan
        try:
            clay = soil_point("clay_0-5cm_mean", lat, lon)  # %
        except:
            clay = np.nan

    # 3) Weather
    with st.spinner("Fetching 7-day weather..."):
        rain7, tmax7 = weather_7d(lat, lon)

    st.subheader("Inputs")
    st.write("NDVI mean:", ndvi_mean)
    st.write("Soil pH:", ph)
    st.write("SOC (g/kg):", soc)
    st.write("Clay (%):", clay)
    st.write("Rain next 7d (mm):", rain7)
    st.write("Avg Tmax next 7d (°C):", tmax7)

    # ---- Simple heuristic model (beta) ----
    # baseline yields (t/ha) — you can edit later
    base = {"Wheat": 4.5, "Corn": 7.0, "Sunflower": 2.6, "Soy": 2.4}[crop]

    # NDVI factor (main)
    ndvi_factor = np.clip((ndvi_mean - 0.2) / 0.6, 0.0, 1.2)  # 0..1.2

    # Soil factor (soft)
    soil_factor = 1.0
    if np.isfinite(ph):
        if ph < 5.5: soil_factor *= 0.92
        elif ph > 7.8: soil_factor *= 0.95
        else: soil_factor *= 1.02
    if np.isfinite(soc):
        if soc < 10: soil_factor *= 0.93
        elif soc > 20: soil_factor *= 1.05
    if np.isfinite(clay):
        if clay > 45: soil_factor *= 0.95

    # Weather factor (next 7 days only, small influence)
    wx_factor = 1.0
    if rain7 < 5: wx_factor *= 0.96
    elif rain7 > 35: wx_factor *= 0.97

    pred = base * (0.65 + 0.55 * ndvi_factor) * soil_factor * wx_factor

    # Confidence
    conf = 0.55
    if np.isfinite(ph) and np.isfinite(soc) and np.isfinite(clay): conf += 0.10
    if ndvi_mean > 0.35: conf += 0.10
    if len(items) > 0: conf += 0.05
    conf = float(np.clip(conf, 0.4, 0.85))

    st.subheader("Result")
    st.metric("Predicted yield (t/ha)", f"{pred:.2f}")
    st.progress(conf)
    st.caption(f"Confidence (beta): {conf:.2f}")

    st.subheader("Why")
    st.write("- NDVI is the strongest signal (current vegetation condition).")
    st.write("- Soil adjusts yield up/down softly (pH, SOC, clay).")
    st.write("- Weather next 7 days adds small correction (drought / too wet).")

    df = pd.DataFrame([{
        "crop": crop,
        "ndvi_mean": ndvi_mean,
        "pH": ph,
        "SOC_gkg": soc,
        "clay_pct": clay,
        "rain7_mm": rain7,
        "pred_t_ha": pred,
        "confidence": conf
    }])
    st.download_button(
        "Download prediction (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"yield_{choice.replace(' ','_')}.csv",
        mime="text/csv",
        key="yield_csv"
    )

