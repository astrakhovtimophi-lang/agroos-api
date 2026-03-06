import streamlit as st
from i18n import tr
from styles import apply_styles

apply_styles()

import json
from pathlib import Path
from shapely.geometry import shape
import folium
from folium.raster_layers import WmsTileLayer
from streamlit_folium import st_folium

st.title(tr("module_soil_map"))
st.caption("Слои как в GIS: спутник/OSM, подписи, граница поля, центроид, несколько слоёв SoilGrids + прозрачность.")

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

choice = st.selectbox("Field", names, key="soil_gis_field")
geom = geoms[names.index(choice)]
poly = shape(geom)

minx, miny, maxx, maxy = poly.bounds  # lon/lat
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2

# --- Controls ---
c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    basemap = st.selectbox("Base map", ["Satellite", "Base map"], index=0, key="soil_gis_basemap")
with c2:
    show_labels = st.checkbox("Labels (roads/places)", value=True, key="soil_gis_labels")
with c3:
    opacity = st.slider("Soil overlay opacity", 0.0, 1.0, 0.55, 0.05, key="soil_gis_opacity")

c4, c5, c6 = st.columns([2, 2, 2])
with c4:
    show_border = st.checkbox("Field border", value=True, key="soil_gis_border")
with c5:
    show_centroid = st.checkbox("Centroid marker", value=False, key="soil_gis_centroid")
with c6:
    zoom = st.slider("Zoom", 8, 18, 13, key="soil_gis_zoom")

st.subheader("SoilGrids layers")
st.caption("Можно включать несколько слоёв одновременно (как в GIS).")

SOIL_LAYERS = {
    "pH (0-5cm)": "phh2o_0-5cm_mean",
    "SOC (0-5cm)": "soc_0-5cm_mean",
    "Clay (0-5cm)": "clay_0-5cm_mean",
    "Sand (0-5cm)": "sand_0-5cm_mean",
    "Silt (0-5cm)": "silt_0-5cm_mean",
}

default_sel = ["pH (0-5cm)"]
selected = st.multiselect("Enable soil layers", list(SOIL_LAYERS.keys()), default=default_sel, key="soil_gis_layers")

WMS_URL = "https://maps.isric.org/mapserv?map=/map/soilgrids.map"

# --- Map ---
m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles=None, control_scale=True)

# Base layers
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satellite",
    overlay=False,
    control=True,
    show=(basemap == "Satellite"),
).add_to(m)

folium.TileLayer(
    tiles="OpenStreetMap",
    name="Base map",
    overlay=False,
    control=True,
    show=(basemap == "Base map"),
).add_to(m)

# Labels overlay (works nice over satellite)
if show_labels:
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
        attr="© CARTO",
        name="Labels",
        overlay=True,
        control=True,
        show=True,
        opacity=0.95
    ).add_to(m)

# Soil overlays (WMS)
for title in selected:
    layer_name = SOIL_LAYERS[title]
    WmsTileLayer(
        url=WMS_URL,
        layers=layer_name,
        fmt="image/png",
        transparent=True,
        name=f"Soil: {title}",
        overlay=True,
        control=True,
        show=True,
        opacity=opacity,
    ).add_to(m)

# Field border
if show_border:
    folium.GeoJson(
        {"type": "Feature", "geometry": geom, "properties": {"name": choice}},
        name="Field border",
        style_function=lambda x: {"color": "#00ff88", "weight": 3, "fillOpacity": 0.0},
        tooltip=choice
    ).add_to(m)

# Centroid marker
if show_centroid:
    c = poly.centroid
    folium.Marker(
        location=[float(c.y), float(c.x)],
        tooltip="Centroid",
        icon=folium.Icon(color="green", icon="info-sign")
    ).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, height=620, width=None)

st.info("Если какой-то soil-слой пустой — скажи какой именно (pH/SOC/Clay/Sand/Silt), подстрою названия под твой WMS.")

