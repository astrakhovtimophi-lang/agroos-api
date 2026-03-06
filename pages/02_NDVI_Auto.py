from datetime import date, timedelta
import io
import json
from pathlib import Path

import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from i18n import tr
from folium.plugins import Draw
from pyproj import Transformer
from pystac_client import Client
from shapely.geometry import mapping, shape
from shapely.ops import transform
from streamlit_folium import st_folium

from agro_utils import add_event, add_ndvi_record
from styles import apply_styles

apply_styles()

st.title(tr("module_ndvi_pro"))
st.caption("Pro workflow: scene quality ranking, cloud masking (SCL), multi-scene composite, advanced metrics and export.")

try:
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.mask import mask
except Exception:
    st.error("rasterio is not installed or failed to import. Install requirements.txt")
    st.stop()


# ---------- Utils ----------
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


def resize_nearest(arr, target_shape):
    src_h, src_w = arr.shape
    dst_h, dst_w = target_shape
    if (src_h, src_w) == (dst_h, dst_w):
        return arr
    row_idx = np.clip(np.linspace(0, src_h - 1, dst_h).astype(int), 0, src_h - 1)
    col_idx = np.clip(np.linspace(0, src_w - 1, dst_w).astype(int), 0, src_w - 1)
    return arr[row_idx[:, None], col_idx[None, :]]


def read_clip(url: str, poly_wgs84):
    with rasterio.open(url) as src:
        if src.crs is None:
            raise ValueError("Raster has no CRS")

        if "4326" in str(src.crs):
            poly_src = poly_wgs84
        else:
            trf = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            poly_src = transform(lambda x, y, z=None: trf.transform(x, y), poly_wgs84)

        out_img, out_transform = mask(src, [mapping(poly_src)], crop=True)
        arr = out_img[0].astype("float32")

        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan

        return arr, out_transform, src.crs


def compute_index(index_name, red, nir, blue=None, red_edge=None):
    if index_name == "NDVI":
        idx = (nir - red) / (nir + red + 1e-6)
    elif index_name == "EVI":
        if blue is None:
            raise ValueError("Blue band is required for EVI")
        idx = 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0 + 1e-6)
    elif index_name == "NDRE":
        if red_edge is None:
            raise ValueError("Red-edge band is required for NDRE")
        idx = (nir - red_edge) / (nir + red_edge + 1e-6)
    else:
        raise ValueError(f"Unsupported index: {index_name}")

    return np.clip(idx.astype("float32"), -1.0, 1.0)


def apply_scl_mask(index_arr, scl_arr, mask_water=False):
    # SCL classes: 3 cloud shadow, 8/9/10 clouds/cirrus, 11 snow/ice
    bad = {3, 8, 9, 10, 11}
    if mask_water:
        bad.add(6)

    scl_i = np.round(scl_arr).astype("int16")
    invalid = np.isin(scl_i, list(bad))

    out = index_arr.copy()
    out[invalid] = np.nan
    return out, float(invalid.mean() * 100.0)


def array_to_geotiff_bytes(arr, transform_affine, crs, nodata=-9999.0):
    out = np.where(np.isfinite(arr), arr, nodata).astype("float32")
    with MemoryFile() as mem:
        with mem.open(
            driver="GTiff",
            height=out.shape[0],
            width=out.shape[1],
            count=1,
            dtype="float32",
            crs=crs,
            transform=transform_affine,
            nodata=nodata,
        ) as dst:
            dst.write(out, 1)
        return mem.read()


# ---------- UI Controls ----------
default_lat = 48.7
default_lon = 33.7

c1, c2, c3 = st.columns(3)
with c1:
    lat = st.number_input("Center lat", value=default_lat, format="%.6f", key="ndvi_lat")
with c2:
    lon = st.number_input("Center lon", value=default_lon, format="%.6f", key="ndvi_lon")
with c3:
    zoom = st.slider("Zoom", 8, 18, 13, key="ndvi_zoom")

d1, d2, d3 = st.columns(3)
with d1:
    start = st.date_input("Start date", value=date.today() - timedelta(days=45), key="ndvi_start")
with d2:
    end = st.date_input("End date", value=date.today() - timedelta(days=1), key="ndvi_end")
with d3:
    max_cloud = st.slider("Max cloud (%)", 0, 80, 50, key="ndvi_cloud")

e1, e2, e3 = st.columns(3)
with e1:
    index_name = st.selectbox("Vegetation index", ["NDVI", "EVI", "NDRE"], index=0)
with e2:
    mode = st.selectbox("Scene strategy", ["Best single scene", "Median composite (top scenes)"], index=1)
with e3:
    top_n = st.slider("Top scenes for composite", 2, 8, 4) if "Median" in mode else 1

f1, f2, f3 = st.columns(3)
with f1:
    use_scl_mask = st.checkbox("Apply SCL cloud mask", value=True)
with f2:
    mask_water = st.checkbox("Mask water class too", value=False)
with f3:
    min_valid_pct = st.slider("Min valid pixels per scene (%)", 20, 95, 55)

save_history = st.checkbox("Save NDVI result to trends history", value=True)

# ---------- Fields linkage ----------
FIELDS_FILE = Path("data") / "fields.geojson"


def load_fields_fc():
    if FIELDS_FILE.exists():
        try:
            return json.loads(FIELDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"type": "FeatureCollection", "features": []}
    return {"type": "FeatureCollection", "features": []}


fc = load_fields_fc()
features = fc.get("features", []) if isinstance(fc, dict) else []

saved_options = ["— Draw on map —"]
saved_geoms = [None]
for f in features:
    props = f.get("properties", {}) if isinstance(f, dict) else {}
    nm = props.get("name") or "field"
    saved_options.append(nm)
    saved_geoms.append(f.get("geometry"))

saved_choice = st.selectbox("Saved field", saved_options, index=0, key="ndvi_saved_field_select")
geom_from_saved = None
if saved_choice != "— Draw on map —":
    geom_from_saved = saved_geoms[saved_options.index(saved_choice)]

st.write("Map: choose a saved field or draw Polygon/Rectangle, then click Build Index.")

m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True, tiles=None)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satellite",
    overlay=False,
    control=True,
).add_to(m)
folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
    attr="© CARTO",
    name="Labels",
    overlay=True,
    control=True,
    opacity=0.9,
).add_to(m)
Draw(
    export=False,
    draw_options={"polyline": False, "rectangle": True, "circle": False, "circlemarker": False, "marker": False, "polygon": True},
    edit_options={"edit": True, "remove": True},
).add_to(m)
folium.LayerControl(collapsed=True).add_to(m)
res = st_folium(m, height=520, width=None)

geom = geom_from_saved
if geom is None and isinstance(res, dict):
    lad = res.get("last_active_drawing")
    if isinstance(lad, dict) and lad.get("geometry"):
        geom = lad["geometry"]

if geom is None:
    st.info("Draw a field polygon/rectangle or choose a saved field.")
    st.stop()

st.success("Field geometry received.")
poly = shape(geom)


# ---------- Processing ----------
if st.button(f"Build {index_name}", key="ndvi_build_pro"):
    with st.spinner("Searching Sentinel-2 scenes..."):
        catalog = Client.open("https://earth-search.aws.element84.com/v1")
        dt = f"{start.isoformat()}/{end.isoformat()}"
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            intersects=geom,
            datetime=dt,
            query={"eo:cloud_cover": {"lt": max_cloud}},
            limit=120,
        )
        items = list(search.items())

    if not items:
        st.error("No scenes found. Try wider date range or higher cloud threshold.")
        st.stop()

    items.sort(key=lambda it: (it.properties.get("eo:cloud_cover", 9999), it.properties.get("datetime", "")))

    preview_rows = []
    for it in items[:20]:
        preview_rows.append(
            {
                "scene": it.id,
                "datetime": str(it.properties.get("datetime", ""))[:19],
                "cloud_pct": float(it.properties.get("eo:cloud_cover", np.nan)),
            }
        )
    st.subheader("Candidate scenes")
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    selected_items = items[: (top_n if "Median" in mode else 1)]

    scene_summaries = []
    scene_arrays = []
    base_shape = None
    base_transform = None
    base_crs = None

    for i, item in enumerate(selected_items):
        red_key = pick_asset(item, ["B04", "red", "SR_B4", "band_4"])
        nir_key = pick_asset(item, ["B08", "nir", "SR_B8", "band_8", "B8A"])
        blue_key = pick_asset(item, ["B02", "blue", "SR_B2", "band_2"])
        re_key = pick_asset(item, ["B05", "rededge", "red_edge", "band_5"])
        scl_key = pick_asset(item, ["SCL", "scl", "scene_classification"])

        if red_key is None or nir_key is None:
            st.warning(f"Skip {item.id}: RED/NIR assets missing")
            continue
        if index_name == "EVI" and blue_key is None:
            st.warning(f"Skip {item.id}: Blue band missing for EVI")
            continue
        if index_name == "NDRE" and re_key is None:
            st.warning(f"Skip {item.id}: Red-edge band missing for NDRE")
            continue

        try:
            red, trf, crs = read_clip(item.assets[red_key].href, poly)
            nir, _, _ = read_clip(item.assets[nir_key].href, poly)

            blue = None
            red_edge = None
            if index_name == "EVI":
                blue, _, _ = read_clip(item.assets[blue_key].href, poly)
            if index_name == "NDRE":
                red_edge, _, _ = read_clip(item.assets[re_key].href, poly)

            idx = compute_index(index_name, red=red, nir=nir, blue=blue, red_edge=red_edge)

            cloud_mask_pct = 0.0
            if use_scl_mask and scl_key is not None:
                scl, _, _ = read_clip(item.assets[scl_key].href, poly)
                scl = resize_nearest(scl, idx.shape)
                idx, cloud_mask_pct = apply_scl_mask(idx, scl, mask_water=mask_water)

            if base_shape is None:
                base_shape = idx.shape
                base_transform = trf
                base_crs = crs
            elif idx.shape != base_shape:
                idx = resize_nearest(idx, base_shape)

            valid_mask = np.isfinite(idx)
            valid_pct = float(valid_mask.mean() * 100.0)
            if valid_pct < min_valid_pct:
                st.warning(f"Skip {item.id}: valid {valid_pct:.1f}% < {min_valid_pct}%")
                continue

            scene_arrays.append(idx)
            scene_summaries.append(
                {
                    "scene": item.id,
                    "datetime": str(item.properties.get("datetime", ""))[:19],
                    "cloud_pct": float(item.properties.get("eo:cloud_cover", np.nan)),
                    "masked_pct": cloud_mask_pct,
                    "valid_pct": valid_pct,
                    f"{index_name}_mean": float(np.nanmean(idx)),
                    f"{index_name}_median": float(np.nanmedian(idx)),
                    "p10": float(np.nanpercentile(idx, 10)),
                    "p90": float(np.nanpercentile(idx, 90)),
                }
            )
        except Exception as e:
            st.warning(f"Skip {item.id}: {e}")

    if not scene_arrays:
        st.error("No valid scenes after quality filters. Relax cloud/valid thresholds or date range.")
        st.stop()

    if "Median" in mode and len(scene_arrays) > 1:
        final_idx = np.nanmedian(np.stack(scene_arrays, axis=0), axis=0)
        result_label = f"{index_name} median composite ({len(scene_arrays)} scenes)"
    else:
        final_idx = scene_arrays[0]
        result_label = f"{index_name} from best scene"

    summary_df = pd.DataFrame(scene_summaries)
    st.subheader("Used scenes summary")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    if len(summary_df) > 1:
        chart_df = summary_df.copy()
        chart_df["datetime"] = pd.to_datetime(chart_df["datetime"], errors="coerce")
        chart_df = chart_df.dropna(subset=["datetime"]).sort_values("datetime")
        if not chart_df.empty:
            st.line_chart(chart_df.set_index("datetime")[[f"{index_name}_mean"]])

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(final_idx, vmin=-1, vmax=1, cmap="RdYlGn")
    ax.set_title(result_label)
    ax.axis("off")
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(index_name)
    st.pyplot(fig, clear_figure=True)

    valid = np.isfinite(final_idx)
    valid_pct_final = float(valid.mean() * 100.0)
    mn = float(np.nanmin(final_idx))
    av = float(np.nanmean(final_idx))
    mx = float(np.nanmax(final_idx))
    p10 = float(np.nanpercentile(final_idx, 10))
    p90 = float(np.nanpercentile(final_idx, 90))

    a, b, c, d, e, f = st.columns(6)
    a.metric("Min", f"{mn:.3f}")
    b.metric("Mean", f"{av:.3f}")
    c.metric("Max", f"{mx:.3f}")
    d.metric("P10", f"{p10:.3f}")
    e.metric("P90", f"{p90:.3f}")
    f.metric("Valid", f"{valid_pct_final:.1f}%")

    # NDVI style classes (still useful baseline for other indices too)
    z_bad = float(np.nanmean(final_idx < 0.2) * 100.0)
    z_mid = float(np.nanmean((final_idx >= 0.2) & (final_idx <= 0.5)) * 100.0)
    z_good = float(np.nanmean(final_idx > 0.5) * 100.0)
    x, y, z = st.columns(3)
    x.metric("Low (<0.2)", f"{z_bad:.1f}%")
    y.metric("Medium (0.2–0.5)", f"{z_mid:.1f}%")
    z.metric("High (>0.5)", f"{z_good:.1f}%")

    fig_h, ax_h = plt.subplots(figsize=(8, 3.2))
    vals = final_idx[np.isfinite(final_idx)].ravel()
    ax_h.hist(vals, bins=40, color="#49D98A", alpha=0.85)
    ax_h.set_title(f"{index_name} distribution")
    ax_h.set_xlabel(index_name)
    ax_h.set_ylabel("Pixels")
    ax_h.grid(alpha=0.2)
    st.pyplot(fig_h, clear_figure=True)

    # Export
    st.subheader("Export")
    st.download_button(
        "Download scene summary (CSV)",
        data=summary_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{index_name.lower()}_scene_summary.csv",
        mime="text/csv",
    )

    if base_transform is not None and base_crs is not None:
        try:
            tif_bytes = array_to_geotiff_bytes(final_idx, base_transform, base_crs)
            st.download_button(
                f"Download {index_name} GeoTIFF",
                data=tif_bytes,
                file_name=f"{index_name.lower()}_result.tif",
                mime="image/tiff",
            )
        except Exception as e:
            st.info(f"GeoTIFF export unavailable: {e}")

    # NDVI history integration
    if index_name == "NDVI" and save_history:
        field_name = saved_choice if saved_choice != "— Draw on map —" else "General"

        if not summary_df.empty:
            summary_dt = str(summary_df.iloc[0]["datetime"])[:10]
            if not summary_dt:
                summary_dt = end.isoformat()
        else:
            summary_dt = end.isoformat()

        add_ndvi_record(field_name, summary_dt, av, source="ndvi_auto_pro")
        add_event(
            field_name=field_name,
            event_type="ndvi_record",
            event_date=summary_dt,
            note=f"NDVI Pro mean={av:.3f}, valid={valid_pct_final:.1f}% ({len(scene_arrays)} scene(s))",
            source="ndvi_auto_pro",
            meta={"mode": mode, "use_scl_mask": use_scl_mask, "max_cloud": max_cloud},
        )
        st.success("NDVI saved to trends history and timeline.")
