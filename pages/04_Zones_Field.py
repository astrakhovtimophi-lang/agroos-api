import io
import json
import zipfile
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from pyproj import Transformer
from pystac_client import Client
from shapely.geometry import mapping, shape
from shapely.ops import transform

from agro_utils import add_event, add_ndvi_record, field_names_and_features
from i18n import ensure_lang
from styles import apply_styles

apply_styles()
ensure_lang()

st.title("🧩 Zones (Field zoning from NDVI)")
st.caption("Build NDVI for a saved field, split it into zones, and export VRA layers.")

try:
    import rasterio
    from rasterio.features import shapes as raster_shapes
    from rasterio.mask import mask
except Exception as e:
    st.error(f"rasterio import failed: {e}")
    st.stop()

try:
    from sklearn.cluster import KMeans
except Exception as e:
    st.error("scikit-learn is missing. Run: pip install -r requirements.txt")
    st.stop()

names, feats = field_names_and_features()
if not names:
    st.warning("No saved fields found. Go to Field Manager (Map) and save a field first.")
    st.stop()

choice = st.selectbox("Saved field", names, key="zones_field_pick")
feat = feats[names.index(choice)]
geom = feat.get("geometry")

c1, c2, c3 = st.columns(3)
with c1:
    start = st.date_input("Start date", value=date.today() - timedelta(days=60), key="zones_start")
with c2:
    end = st.date_input("End date", value=date.today() - timedelta(days=1), key="zones_end")
with c3:
    max_cloud = st.slider("Max cloud (%)", 0, 90, 50, key="zones_cloud")

k = st.slider("Number of zones", 3, 5, 4, key="zones_k")
base_n = st.number_input("Base N rate (kg/ha)", min_value=20.0, max_value=300.0, value=120.0, step=5.0)
base_seed = st.number_input("Base seed rate (kg/ha)", min_value=20.0, max_value=400.0, value=180.0, step=5.0)


def pick_asset(item, candidates):
    keys = list(item.assets.keys())
    for c in candidates:
        if c in item.assets:
            return c
    for c in candidates:
        for kk in keys:
            if c.lower() in kk.lower():
                return kk
    return None


def read_clip(url: str, poly_wgs84):
    with rasterio.open(url) as src:
        if src.crs is None:
            raise ValueError("Raster has no CRS")

        if "4326" in str(src.crs):
            poly_src = poly_wgs84
        else:
            to_src = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            poly_src = transform(lambda x, y, z=None: to_src.transform(x, y), poly_wgs84)

        out_img, out_transform = mask(src, [mapping(poly_src)], crop=True)
        arr = out_img[0].astype("float32")
        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan
        return arr, out_transform, src.crs


def zone_recommendations(df_stats: pd.DataFrame, n_base: float, seed_base: float):
    stats = {}
    if df_stats.empty:
        return stats

    ndvi_min = float(df_stats["ndvi_mean"].min())
    ndvi_max = float(df_stats["ndvi_mean"].max())
    den = max(ndvi_max - ndvi_min, 1e-6)

    for _, row in df_stats.iterrows():
        z = int(row["zone"])
        mean_ndvi = float(row["ndvi_mean"])
        norm = (mean_ndvi - ndvi_min) / den

        n_rate = round(n_base * (1.2 - 0.4 * norm), 1)
        seed_rate = round(seed_base * (1.12 - 0.24 * norm), 1)

        if norm < 0.33:
            action = "boost"
        elif norm < 0.66:
            action = "maintain"
        else:
            action = "reduce"

        stats[z] = {
            "zone": z,
            "ndvi_mean": round(mean_ndvi, 4),
            "vra_action": action,
            "n_rate_kg_ha": n_rate,
            "seed_rate_kg_ha": seed_rate,
        }
    return stats


def build_zone_geojson(labels, affine_transform, raster_crs, zone_meta):
    out_features = []
    valid_mask = labels >= 0

    to_wgs84 = None
    if raster_crs and "4326" not in str(raster_crs):
        transformer = Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True)
        to_wgs84 = lambda x, y, z=None: transformer.transform(x, y)

    for geom_json, val in raster_shapes(labels.astype("int16"), mask=valid_mask, transform=affine_transform):
        zone_id = int(val)
        if zone_id not in zone_meta:
            continue

        poly = shape(geom_json)
        if poly.is_empty or poly.area <= 0:
            continue

        if to_wgs84 is not None:
            poly = transform(to_wgs84, poly)

        props = dict(zone_meta[zone_id])
        out_features.append(
            {
                "type": "Feature",
                "geometry": mapping(poly),
                "properties": props,
            }
        )

    return {"type": "FeatureCollection", "features": out_features}


def geojson_to_shapefile_zip(geojson_obj):
    try:
        import shapefile  # pyshp
    except Exception:
        return None, "Install pyshp for Shapefile export: pip install pyshp"

    features = geojson_obj.get("features", [])
    if not features:
        return None, "No zone polygons to export."

    wgs84_prj = (
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
    )

    with TemporaryDirectory() as td:
        base = Path(td) / "zones_vra"
        writer = shapefile.Writer(str(base), shapeType=shapefile.POLYGON)
        writer.field("zone", "N", size=6, decimal=0)
        writer.field("ndvi_mean", "F", size=10, decimal=4)
        writer.field("action", "C", size=12)
        writer.field("n_rate", "F", size=10, decimal=1)
        writer.field("seed_rate", "F", size=10, decimal=1)

        written = 0
        for ft in features:
            geom = ft.get("geometry") or {}
            props = ft.get("properties") or {}
            gtype = geom.get("type")
            coords = geom.get("coordinates") or []

            parts = []
            if gtype == "Polygon":
                parts = [[[x, y] for x, y in ring] for ring in coords]
            elif gtype == "MultiPolygon":
                for poly in coords:
                    for ring in poly:
                        parts.append([[x, y] for x, y in ring])

            if not parts:
                continue

            writer.poly(parts)
            writer.record(
                int(props.get("zone", -1)),
                float(props.get("ndvi_mean", 0.0)),
                str(props.get("vra_action", "maintain"))[:12],
                float(props.get("n_rate_kg_ha", 0.0)),
                float(props.get("seed_rate_kg_ha", 0.0)),
            )
            written += 1

        writer.close()

        if written == 0:
            return None, "No polygons were written to shapefile."

        (base.with_suffix(".prj")).write_text(wgs84_prj, encoding="utf-8")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                p = base.with_suffix(ext)
                if p.exists():
                    zf.write(p, arcname=p.name)

        return buf.getvalue(), None


if st.button("Build zones", key="zones_build"):
    with st.spinner("Searching Sentinel-2 scenes..."):
        catalog = Client.open("https://earth-search.aws.element84.com/v1")
        dt = f"{start.isoformat()}/{end.isoformat()}"
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            intersects=geom,
            datetime=dt,
            query={"eo:cloud_cover": {"lt": max_cloud}},
            limit=150,
        )
        items = list(search.items())

    if not items:
        st.error("No scenes found. Try wider date range or higher cloud threshold.")
        st.stop()

    items.sort(key=lambda it: (it.properties.get("eo:cloud_cover", 9999), it.properties.get("datetime", "")))
    item = items[0]
    st.write("Scene:", item.id)
    st.write("Cloud %:", item.properties.get("eo:cloud_cover"))
    st.write("Datetime:", item.properties.get("datetime"))

    red_key = pick_asset(item, ["B04", "red", "SR_B4", "band_4"])
    nir_key = pick_asset(item, ["B08", "nir", "SR_B8", "band_8", "B8A"])
    if red_key is None or nir_key is None:
        st.error("RED/NIR assets not found in this scene.")
        st.write(list(item.assets.keys())[:60])
        st.stop()

    red_url = item.assets[red_key].href
    nir_url = item.assets[nir_key].href

    poly = shape(geom)
    with st.spinner("Downloading bands + computing NDVI..."):
        red, red_affine, red_crs = read_clip(red_url, poly)
        nir, nir_affine, nir_crs = read_clip(nir_url, poly)

        if red.shape != nir.shape:
            st.error("Band alignment mismatch. Try another scene/date range.")
            st.stop()

        ndvi = (nir - red) / (nir + red + 1e-6)
        ndvi = np.clip(ndvi, -1.0, 1.0)

    valid = np.isfinite(ndvi)
    vals = ndvi[valid].reshape(-1, 1)

    if vals.shape[0] < 200:
        st.error("Too few valid pixels (maybe clouds / geometry mismatch). Try another date range.")
        st.stop()

    with st.spinner(f"Clustering into {k} zones..."):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = np.full(ndvi.shape, fill_value=-1, dtype=np.int16)
        labs = km.fit_predict(vals)
        labels[valid] = labs

    colA, colB = st.columns(2)
    with colA:
        fig1 = plt.figure()
        plt.imshow(ndvi, vmin=-1, vmax=1)
        plt.title("NDVI")
        plt.axis("off")
        st.pyplot(fig1, clear_figure=True)

    with colB:
        fig2 = plt.figure()
        plt.imshow(labels, vmin=0, vmax=k - 1)
        plt.title(f"Zones (0..{k-1})")
        plt.axis("off")
        st.pyplot(fig2, clear_figure=True)

    rows = []
    total = int(valid.sum())
    for z in range(k):
        m = labels == z
        cnt = int(m.sum())
        if cnt == 0:
            continue
        rows.append(
            {
                "zone": z,
                "pixels": cnt,
                "percent": round(cnt / max(total, 1) * 100.0, 2),
                "ndvi_mean": float(np.nanmean(ndvi[m])),
                "ndvi_min": float(np.nanmin(ndvi[m])),
                "ndvi_max": float(np.nanmax(ndvi[m])),
            }
        )

    df = pd.DataFrame(rows).sort_values("ndvi_mean", ascending=False)
    st.subheader("Zone stats")
    st.dataframe(df, use_container_width=True)

    mean_ndvi = float(np.nanmean(ndvi))
    dt_scene = str(item.properties.get("datetime") or "")[:10] or date.today().isoformat()
    add_ndvi_record(choice, dt_scene, mean_ndvi, source="zones_auto")
    add_event(
        field_name=choice,
        event_type="ndvi_zoning",
        event_date=dt_scene,
        note=f"NDVI zoning built from scene {item.id}. Mean NDVI={mean_ndvi:.3f}",
        source="zones_page",
    )

    st.success(f"Saved NDVI record for trends: {mean_ndvi:.3f}")

    st.download_button(
        "Download zone stats (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"zones_{choice.replace(' ', '_')}.csv",
        mime="text/csv",
        key="zones_csv",
    )

    zone_meta = zone_recommendations(df, n_base=base_n, seed_base=base_seed)
    geojson_obj = build_zone_geojson(labels, red_affine, red_crs, zone_meta)
    geojson_bytes = json.dumps(geojson_obj, ensure_ascii=False, indent=2).encode("utf-8")

    st.subheader("VRA export")
    st.caption("Each zone contains recommended N and seeding rates based on NDVI class.")

    st.download_button(
        "Download VRA zones (GeoJSON)",
        data=geojson_bytes,
        file_name=f"vra_zones_{choice.replace(' ', '_')}.geojson",
        mime="application/geo+json",
        key="zones_geojson",
    )

    shp_zip, shp_err = geojson_to_shapefile_zip(geojson_obj)
    if shp_zip is not None:
        st.download_button(
            "Download VRA zones (Shapefile ZIP)",
            data=shp_zip,
            file_name=f"vra_zones_{choice.replace(' ', '_')}.zip",
            mime="application/zip",
            key="zones_shp",
        )
    else:
        st.info(shp_err)

