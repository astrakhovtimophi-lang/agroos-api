import json
from pathlib import Path

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

from styles import apply_styles

apply_styles()

st.title("🗺 Field Manager (Map)")

DATA = Path("data")
DATA.mkdir(exist_ok=True)
FIELDS_FILE = DATA / "fields.geojson"


def load_fields():
    if FIELDS_FILE.exists():
        try:
            return json.loads(FIELDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"type": "FeatureCollection", "features": []}


def save_fields(fc):
    FIELDS_FILE.write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding="utf-8")


fc = load_fields()
features = fc.get("features", [])

# --- Import from file ---
with st.expander("⬆️ Import field boundaries (GeoJSON)", expanded=False):
    uploaded = st.file_uploader("Upload GeoJSON", type=["geojson", "json"], key="fm_geojson_upload")
    default_status = st.selectbox("Default status for imported fields", ["Розміновано", "Не розміновано"], key="fm_import_status")

    if uploaded is not None:
        try:
            incoming = json.loads(uploaded.getvalue().decode("utf-8"))
            incoming_features = incoming.get("features", []) if isinstance(incoming, dict) else []
            st.write(f"Detected features: {len(incoming_features)}")
        except Exception as e:
            st.error(f"Invalid file: {e}")
            incoming_features = []

        if incoming_features and st.button("Import features", key="fm_import_btn"):
            added = 0
            existing_names = {(f.get("properties", {}) or {}).get("name", "") for f in features}

            for idx, f in enumerate(incoming_features, start=1):
                if not isinstance(f, dict):
                    continue
                geom = f.get("geometry")
                if not geom:
                    continue

                props = f.get("properties", {}) or {}
                nm = str(props.get("name") or props.get("field") or f"Imported_{idx}").strip()
                if nm in existing_names:
                    nm = f"{nm}_{idx}"

                fc["features"].append(
                    {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": {
                            "name": nm,
                            "status": str(props.get("status") or default_status),
                        },
                    }
                )
                added += 1

            save_fields(fc)
            st.success(f"Imported fields: {added}")
            st.rerun()

# --- UI: filter + add field meta ---
c1, c2 = st.columns([2, 2])
with c1:
    status_filter = st.selectbox("Фільтр полів", ["Всі", "Розміновано", "Не розміновано"], key="fm_filter")
with c2:
    map_style = st.selectbox("Map style", ["Satellite", "Base map"], index=0, key="fm_map_style")

st.caption("Намалюй поле (Polygon/Rectangle) зліва на мапі → введи назву → обери статус → Зберегти поле.")

# --- Map: Satellite default ---
m = folium.Map(location=[48.7, 33.7], zoom_start=12, tiles=None, control_scale=True)

sat = folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="Satellite",
    overlay=False,
    control=True,
    show=(map_style == "Satellite"),
)
osm = folium.TileLayer(
    tiles="OpenStreetMap",
    name="Base map",
    overlay=False,
    control=True,
    show=(map_style == "Base map"),
)

sat.add_to(m)
osm.add_to(m)

Draw(
    export=False,
    draw_options={"polyline": False, "circle": False, "circlemarker": False, "marker": False},
    edit_options={"edit": True, "remove": True},
).add_to(m)

for f in features:
    props = f.get("properties", {}) or {}
    status = props.get("status", "Розміновано")
    if status_filter != "Всі" and status != status_filter:
        continue

    color = "#00ff88" if status == "Розміновано" else "#ff3b3b"
    folium.GeoJson(
        f,
        name=props.get("name", "field"),
        style_function=lambda x, color=color: {"color": color, "weight": 3, "fillOpacity": 0.15},
        tooltip=f"{props.get('name', 'field')} • {status}",
    ).add_to(m)

folium.LayerControl(collapsed=True).add_to(m)
res = st_folium(m, height=600, width=None)

# --- Save new field ---
st.subheader("➕ Add field")
name = st.text_input("Назва поля", placeholder="Напр. Поле 1", key="fm_name")
status = st.selectbox("Статус поля", ["Розміновано", "Не розміновано"], key="fm_status")

if st.button("Зберегти поле", key="fm_save"):
    lad = (res or {}).get("last_active_drawing")
    geom = None
    if isinstance(lad, dict):
        geom = lad.get("geometry")

    if not geom:
        st.error("Немає намальованого поля. Намалюй полігон/прямокутник на мапі.")
        st.stop()

    if not name.strip():
        st.error("Введи назву поля.")
        st.stop()

    fc["features"].append(
        {
            "type": "Feature",
            "geometry": geom,
            "properties": {"name": name.strip(), "status": status},
        }
    )
    save_fields(fc)
    st.success("Поле збережено ✅")

st.divider()

# --- List / delete fields ---
st.subheader("📋 Saved fields")
features = load_fields().get("features", [])
if not features:
    st.info("Поки що немає збережених полів.")
else:
    labels = [f'{(f.get("properties", {}) or {}).get("name", "field")} • {(f.get("properties", {}) or {}).get("status", "")}' for f in features]
    del_idx = st.selectbox("Видалити поле", ["—"] + labels, key="fm_del_pick")
    if st.button("🗑 Delete selected", key="fm_del_btn"):
        if del_idx == "—":
            st.warning("Обери поле для видалення.")
        else:
            i = labels.index(del_idx)
            features.pop(i)
            save_fields({"type": "FeatureCollection", "features": features})
            st.success("Видалено ✅")
            st.rerun()
