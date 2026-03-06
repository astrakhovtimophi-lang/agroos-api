from collections import defaultdict

import pandas as pd
import streamlit as st
from i18n import tr
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

from agro_utils import (
    field_names_and_features,
    load_crop_plan,
    load_economics,
    load_field_groups,
    load_ndvi_history,
    now_iso,
    save_field_groups,
)
from styles import apply_styles

apply_styles()

st.title(tr("module_field_groups"))
st.caption("Group fields, rank them by metrics, and compare performance side by side.")

field_names, field_feats = field_names_and_features()
if not field_names:
    st.info("No saved fields yet. Open Field Manager and add fields first.")
    st.stop()


def area_ha_from_geom(geom):
    try:
        poly = shape(geom)
        trf = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        poly_m = transform(lambda x, y, z=None: trf.transform(x, y), poly)
        return float(poly_m.area / 10000.0)
    except Exception:
        return None


def latest_crop_for_field(field_name, crop_plans):
    rows = [r for r in crop_plans if str(r.get("field")) == str(field_name)]
    if not rows:
        return "-"
    rows.sort(key=lambda x: (str(x.get("season", "")), str(x.get("created_at", ""))))
    return str(rows[-1].get("crop") or "-")


def latest_ndvi_for_field(field_name, ndvi_rows):
    rows = [r for r in ndvi_rows if str(r.get("field")) == str(field_name)]
    if not rows:
        return None
    rows.sort(key=lambda x: str(x.get("date") or ""))
    try:
        return float(rows[-1].get("ndvi_mean"))
    except Exception:
        return None


def avg_yield_for_field(field_name, econ_rows):
    rows = [r for r in econ_rows if str(r.get("field")) == str(field_name)]
    vals = []
    for r in rows:
        try:
            vals.append(float(r.get("yield_t_ha")))
        except Exception:
            pass
    if not vals:
        return None
    return float(sum(vals) / len(vals))


crop_plans = load_crop_plan()
ndvi_rows = load_ndvi_history()
econ_rows = load_economics()

field_groups = load_field_groups()
field_to_groups = defaultdict(list)
for g in field_groups:
    gname = str(g.get("group") or "").strip()
    for fn in g.get("fields", []):
        field_to_groups[str(fn)].append(gname)

rows = []
for i, feat in enumerate(field_feats):
    props = feat.get("properties", {}) or {}
    name = str(props.get("name") or field_names[i])
    geom = feat.get("geometry")

    area_ha = area_ha_from_geom(geom) if geom else None
    crop = latest_crop_for_field(name, crop_plans)
    ndvi = latest_ndvi_for_field(name, ndvi_rows)
    yld = avg_yield_for_field(name, econ_rows)
    groups = ", ".join(sorted(set(field_to_groups.get(name, []))))

    rows.append(
        {
            "field": name,
            "groups": groups if groups else "-",
            "area_ha": area_ha,
            "crop": crop,
            "ndvi_latest": ndvi,
            "yield_t_ha_avg": yld,
        }
    )

df = pd.DataFrame(rows)

st.subheader("Groups")
with st.form("group_add", clear_on_submit=True):
    g1, g2 = st.columns([1, 2])
    with g1:
        group_name = st.text_input("Group name", placeholder="North block")
    with g2:
        group_fields = st.multiselect("Fields", sorted(df["field"].tolist()))
    save_btn = st.form_submit_button("Save group")

if save_btn and group_name.strip():
    gname = group_name.strip()
    found = None
    for g in field_groups:
        if str(g.get("group")) == gname:
            found = g
            break

    if found is None:
        field_groups.append({"group": gname, "fields": group_fields, "updated_at": now_iso()})
    else:
        found["fields"] = group_fields
        found["updated_at"] = now_iso()

    save_field_groups(field_groups)
    st.success("Group saved.")
    st.rerun()

if field_groups:
    gdf = pd.DataFrame(field_groups)
    st.dataframe(gdf, use_container_width=True, hide_index=True)

    del_group = st.selectbox("Delete group", ["—"] + [str(x.get("group")) for x in field_groups])
    if st.button("Delete selected group"):
        if del_group != "—":
            field_groups = [x for x in field_groups if str(x.get("group")) != del_group]
            save_field_groups(field_groups)
            st.success("Group deleted.")
            st.rerun()

st.subheader("Field list")
sort_by = st.selectbox("Sort by", ["field", "groups", "area_ha", "crop", "ndvi_latest", "yield_t_ha_avg"], index=0)
asc = st.checkbox("Ascending", value=True)
view = df.sort_values(sort_by, ascending=asc, na_position="last")
st.dataframe(view, use_container_width=True, hide_index=True)

st.subheader("Compare fields")
compare_fields = st.multiselect("Choose fields (2-6)", sorted(df["field"].tolist()), default=sorted(df["field"].tolist())[:2])
if len(compare_fields) >= 2:
    cmp = df[df["field"].isin(compare_fields)].copy()
    st.dataframe(cmp, use_container_width=True, hide_index=True)

    metrics_df = cmp.set_index("field")[["area_ha", "ndvi_latest", "yield_t_ha_avg"]]
    metrics_df = metrics_df.fillna(0.0)
    st.bar_chart(metrics_df)

    st.download_button(
        "Download compared fields CSV",
        data=cmp.to_csv(index=False).encode("utf-8"),
        file_name="fields_compare.csv",
        mime="text/csv",
    )
else:
    st.info("Pick at least two fields for comparison.")
