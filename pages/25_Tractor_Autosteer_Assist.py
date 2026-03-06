from __future__ import annotations

import json
import math
from datetime import date
from typing import Any, Dict, List, Tuple

import folium
import numpy as np
import pandas as pd
import streamlit as st
from i18n import tr
from folium.plugins import Draw
from pyproj import Transformer
from shapely.affinity import rotate
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Polygon, mapping, shape
from shapely.ops import transform
from streamlit_folium import st_folium

from agro_utils import add_event, append_autosteer_plan, field_names_and_features, load_autosteer_plans, now_iso
from styles import apply_styles

apply_styles()

st.title(tr("module_autosteer"))
st.caption("Route planning for field operations: AB passes, overlap control, turn model, estimate of time and distance.")
st.warning("Safety: this module does not control machinery. It only generates a route plan for the operator.")


def utm_epsg_for_lon_lat(lon: float, lat: float) -> int:
    zone = int((lon + 180.0) // 6.0) + 1
    return (32600 + zone) if lat >= 0 else (32700 + zone)


def make_transformers(lon: float, lat: float) -> Tuple[Transformer, Transformer, int]:
    epsg = utm_epsg_for_lon_lat(lon, lat)
    to_metric = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    to_wgs84 = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    return to_metric, to_wgs84, epsg


def reproject_geom(geom, transformer: Transformer):
    return transform(lambda x, y, z=None: transformer.transform(x, y), geom)


def largest_polygon(geom):
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        geoms = list(geom.geoms)
        if not geoms:
            return None
        return max(geoms, key=lambda g: g.area)
    return None


def collect_lines(geom) -> List[LineString]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return [g for g in geom.geoms if isinstance(g, LineString) and not g.is_empty]
    if isinstance(geom, GeometryCollection):
        lines: List[LineString] = []
        for g in geom.geoms:
            lines.extend(collect_lines(g))
        return lines
    return []


def heading_name(heading_deg: float) -> str:
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int(round((heading_deg % 360.0) / 45.0)) % 8
    return names[idx]


def quick_rectangle_wgs84(center_lat: float, center_lon: float, length_m: float, width_m: float, azimuth_deg: float):
    to_m, to_wgs, _ = make_transformers(center_lon, center_lat)
    cx, cy = to_m.transform(center_lon, center_lat)
    half_l = max(1.0, float(length_m)) / 2.0
    half_w = max(1.0, float(width_m)) / 2.0

    rect = Polygon(
        [
            (cx - half_w, cy - half_l),
            (cx + half_w, cy - half_l),
            (cx + half_w, cy + half_l),
            (cx - half_w, cy + half_l),
            (cx - half_w, cy - half_l),
        ]
    )
    rect = rotate(rect, -float(azimuth_deg), origin=(cx, cy), use_radians=False)
    return reproject_geom(rect, to_wgs)


def build_autosteer_plan(
    boundary_wgs84,
    heading_deg: float,
    implement_width_m: float,
    overlap_pct: float,
    speed_kmh: float,
    turn_type: str,
    turn_radius_m: float,
    min_pass_len_m: float,
    headland_laps: int,
) -> Dict[str, Any]:
    poly = largest_polygon(boundary_wgs84)
    if poly is None or poly.is_empty:
        raise ValueError("Boundary polygon is empty or invalid.")

    lon0 = float(poly.centroid.x)
    lat0 = float(poly.centroid.y)
    to_m, to_wgs, epsg = make_transformers(lon0, lat0)
    poly_m = reproject_geom(poly, to_m)

    overlap_ratio = float(np.clip(overlap_pct / 100.0, 0.0, 0.95))
    spacing_m = max(0.5, float(implement_width_m) * (1.0 - overlap_ratio))
    headland_offset_m = max(0.0, float(headland_laps) * spacing_m)

    if headland_offset_m > 0:
        inner = poly_m.buffer(-headland_offset_m)
        inner_poly = largest_polygon(inner)
        if inner_poly is None or inner_poly.is_empty:
            inner_poly = poly_m
    else:
        inner_poly = poly_m

    if inner_poly.area <= 0:
        inner_poly = poly_m

    rotated = rotate(inner_poly, -float(heading_deg), origin=inner_poly.centroid, use_radians=False)
    minx, miny, maxx, maxy = rotated.bounds

    x_start = minx + spacing_m / 2.0
    if x_start > maxx:
        x_start = minx
    x_values = np.arange(x_start, maxx + spacing_m, spacing_m)

    lines_wgs: List[LineString] = []
    line_lengths_m: List[float] = []
    rows: List[Dict[str, Any]] = []

    flip = False
    idx = 1
    for x in x_values:
        scan_line = LineString([(float(x), float(miny - 40.0)), (float(x), float(maxy + 40.0))])
        intersections = collect_lines(rotated.intersection(scan_line))
        intersections = [seg for seg in intersections if seg.length >= float(min_pass_len_m)]
        intersections.sort(key=lambda s: float(s.centroid.y))

        for seg in intersections:
            coords = list(seg.coords)
            if coords[0][1] > coords[-1][1]:
                coords.reverse()
            if flip:
                coords.reverse()
            flip = not flip

            ordered = LineString(coords)
            original_m = rotate(ordered, float(heading_deg), origin=inner_poly.centroid, use_radians=False)
            original_wgs = reproject_geom(original_m, to_wgs)
            start_lon, start_lat = original_wgs.coords[0]
            end_lon, end_lat = original_wgs.coords[-1]

            length_m = float(original_m.length)
            lines_wgs.append(original_wgs)
            line_lengths_m.append(length_m)
            rows.append(
                {
                    "pass": idx,
                    "start_lat": round(float(start_lat), 7),
                    "start_lon": round(float(start_lon), 7),
                    "end_lat": round(float(end_lat), 7),
                    "end_lon": round(float(end_lon), 7),
                    "length_m": round(length_m, 1),
                }
            )
            idx += 1

    pass_count = len(rows)
    pass_length_m = float(sum(line_lengths_m))
    area_ha = float(poly_m.area) / 10000.0
    covered_ha = min(area_ha, (pass_length_m * spacing_m) / 10000.0) if area_ha > 0 else 0.0

    turn_count = max(0, pass_count - 1)
    turn_factor = {"U-turn": 1.0, "Y-turn": 0.8, "Skip-turn": 0.55}.get(turn_type, 1.0)
    turn_time_s = {"U-turn": 16.0, "Y-turn": 13.0, "Skip-turn": 9.0}.get(turn_type, 16.0)
    turn_extra_m = turn_count * math.pi * max(1.0, float(turn_radius_m)) * turn_factor
    headland_distance_m = float(poly_m.exterior.length) * max(0, int(headland_laps))

    speed_mps = max(0.3, float(speed_kmh) / 3.6)
    total_distance_m = pass_length_m + turn_extra_m + headland_distance_m
    total_time_h = (pass_length_m + headland_distance_m) / speed_mps / 3600.0 + (turn_count * turn_time_s) / 3600.0

    plan = {
        "epsg": epsg,
        "field_area_ha": round(area_ha, 2),
        "covered_area_ha": round(covered_ha, 2),
        "pass_count": pass_count,
        "spacing_m": round(spacing_m, 2),
        "passes_length_km": round(pass_length_m / 1000.0, 2),
        "turns_count": turn_count,
        "headland_distance_km": round(headland_distance_m / 1000.0, 2),
        "route_distance_km": round(total_distance_m / 1000.0, 2),
        "estimated_time_h": round(total_time_h, 2),
        "heading_deg": round(float(heading_deg), 1),
        "heading_name": heading_name(float(heading_deg)),
        "lines_wgs": lines_wgs,
        "rows": rows,
        "boundary_wgs": poly,
        "inner_wgs": reproject_geom(inner_poly, to_wgs),
    }
    return plan


st.subheader("1) Boundary setup")

field_names, field_features = field_names_and_features()
feature_by_name = {n: f for n, f in zip(field_names, field_features)}

boundary_mode = st.radio("Boundary source", ["Saved field", "Draw boundary", "Quick rectangle"], horizontal=True)

boundary_geom = None
boundary_label = "Custom"

if boundary_mode == "Saved field":
    if not field_names:
        st.info("No saved fields found. Use Draw boundary or Quick rectangle.")
    else:
        selected_field = st.selectbox("Field", field_names, index=0)
        boundary_label = selected_field
        feat = feature_by_name.get(selected_field)
        try:
            boundary_geom = largest_polygon(shape(feat.get("geometry")))
        except Exception:
            boundary_geom = None
            st.error("Cannot read selected field geometry.")

elif boundary_mode == "Draw boundary":
    c1, c2, c3 = st.columns(3)
    with c1:
        draw_lat = st.number_input("Map center lat", value=48.700000, format="%.6f")
    with c2:
        draw_lon = st.number_input("Map center lon", value=33.700000, format="%.6f")
    with c3:
        draw_zoom = st.slider("Zoom", 9, 18, 13)

    draw_map = folium.Map(location=[draw_lat, draw_lon], zoom_start=draw_zoom, control_scale=True, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles Copyright Esri",
        name="Satellite",
        overlay=False,
        control=True,
    ).add_to(draw_map)
    folium.TileLayer(tiles="OpenStreetMap", name="Base map", overlay=False, control=True).add_to(draw_map)
    Draw(
        export=False,
        draw_options={"polyline": False, "circle": False, "circlemarker": False, "marker": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(draw_map)
    folium.LayerControl(collapsed=True).add_to(draw_map)

    draw_res = st_folium(draw_map, height=430, width=None, key="autosteer_draw_boundary")
    last_draw = (draw_res or {}).get("last_active_drawing")
    if isinstance(last_draw, dict) and isinstance(last_draw.get("geometry"), dict):
        try:
            boundary_geom = largest_polygon(shape(last_draw["geometry"]))
            boundary_label = "Drawn boundary"
            if boundary_geom is not None:
                st.session_state["autosteer_draw_boundary_geojson"] = mapping(boundary_geom)
        except Exception:
            boundary_geom = None

    if boundary_geom is None:
        cached_geom = st.session_state.get("autosteer_draw_boundary_geojson")
        if isinstance(cached_geom, dict):
            try:
                boundary_geom = largest_polygon(shape(cached_geom))
                boundary_label = "Drawn boundary"
            except Exception:
                boundary_geom = None

    if boundary_geom is None:
        st.caption("Draw a Polygon/Rectangle on the map to create an autopilot route.")

else:
    r1, r2, r3 = st.columns(3)
    with r1:
        rect_lat = st.number_input("Center lat", value=48.700000, format="%.6f")
    with r2:
        rect_lon = st.number_input("Center lon", value=33.700000, format="%.6f")
    with r3:
        rect_az = st.slider("Rectangle azimuth (deg)", 0, 359, 0)

    r4, r5 = st.columns(2)
    with r4:
        rect_len = st.number_input("Length (m)", min_value=20.0, value=650.0, step=10.0)
    with r5:
        rect_wid = st.number_input("Width (m)", min_value=20.0, value=320.0, step=10.0)

    boundary_geom = quick_rectangle_wgs84(
        center_lat=float(rect_lat),
        center_lon=float(rect_lon),
        length_m=float(rect_len),
        width_m=float(rect_wid),
        azimuth_deg=float(rect_az),
    )
    boundary_label = f"Rectangle {int(rect_len)}x{int(rect_wid)}m"


st.subheader("2) AutoSteer settings")
with st.form("autosteer_plan_form"):
    a1, a2, a3 = st.columns(3)
    with a1:
        plan_name = st.text_input("Plan name", value=f"AutoSteer {date.today().isoformat()}")
    with a2:
        heading_deg = st.slider("AB heading (deg from North)", 0, 359, 0)
    with a3:
        speed_kmh = st.number_input("Target speed (km/h)", min_value=1.0, value=9.0, step=0.5)

    b1, b2, b3 = st.columns(3)
    with b1:
        implement_width_m = st.number_input("Implement width (m)", min_value=1.0, value=24.0, step=0.5)
    with b2:
        overlap_pct = st.slider("Overlap (%)", 0, 40, 7)
    with b3:
        min_pass_len_m = st.number_input("Min pass length (m)", min_value=5.0, value=25.0, step=1.0)

    c1, c2, c3 = st.columns(3)
    with c1:
        turn_type = st.selectbox("Turn model", ["U-turn", "Y-turn", "Skip-turn"], index=0)
    with c2:
        turn_radius_m = st.number_input("Turn radius (m)", min_value=2.0, value=8.0, step=0.5)
    with c3:
        headland_laps = st.slider("Headland laps", 0, 4, 1)

    generate_plan = st.form_submit_button("Generate AutoSteer plan", type="primary")

if generate_plan:
    if boundary_geom is None:
        st.error("Boundary is not set. Choose a source and provide a valid polygon.")
    else:
        try:
            plan = build_autosteer_plan(
                boundary_wgs84=boundary_geom,
                heading_deg=float(heading_deg),
                implement_width_m=float(implement_width_m),
                overlap_pct=float(overlap_pct),
                speed_kmh=float(speed_kmh),
                turn_type=str(turn_type),
                turn_radius_m=float(turn_radius_m),
                min_pass_len_m=float(min_pass_len_m),
                headland_laps=int(headland_laps),
            )

            st.session_state["autosteer_plan_data"] = {
                "plan_name": plan_name.strip() or f"AutoSteer {date.today().isoformat()}",
                "boundary_mode": boundary_mode,
                "field": boundary_label,
                "settings": {
                    "heading_deg": float(heading_deg),
                    "implement_width_m": float(implement_width_m),
                    "overlap_pct": float(overlap_pct),
                    "speed_kmh": float(speed_kmh),
                    "turn_type": str(turn_type),
                    "turn_radius_m": float(turn_radius_m),
                    "min_pass_len_m": float(min_pass_len_m),
                    "headland_laps": int(headland_laps),
                },
                "summary": {k: v for k, v in plan.items() if k not in {"lines_wgs", "rows", "boundary_wgs", "inner_wgs"}},
                "rows": plan["rows"],
                "boundary_wgs": plan["boundary_wgs"],
                "inner_wgs": plan["inner_wgs"],
                "lines_wgs": plan["lines_wgs"],
            }
        except Exception as e:
            st.error(f"Route generation failed: {e}")


plan_data = st.session_state.get("autosteer_plan_data")
if plan_data:
    st.subheader("3) Plan summary and preview")
    summary = plan_data["summary"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Area (ha)", summary.get("field_area_ha", 0))
    m2.metric("Passes", summary.get("pass_count", 0))
    m3.metric("Route (km)", summary.get("route_distance_km", 0))
    m4.metric("ETA (h)", summary.get("estimated_time_h", 0))

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Spacing (m)", summary.get("spacing_m", 0))
    m6.metric("Pass length (km)", summary.get("passes_length_km", 0))
    m7.metric("Turns", summary.get("turns_count", 0))
    m8.metric("Heading", f"{summary.get('heading_deg', 0)} deg ({summary.get('heading_name', 'N')})")

    map_center = plan_data["boundary_wgs"].centroid
    preview = folium.Map(location=[float(map_center.y), float(map_center.x)], zoom_start=14, control_scale=True, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles Copyright Esri",
        name="Satellite",
        overlay=False,
        control=True,
    ).add_to(preview)
    folium.TileLayer(tiles="OpenStreetMap", name="Base map", overlay=False, control=True).add_to(preview)

    folium.GeoJson(
        data=mapping(plan_data["boundary_wgs"]),
        name="Field boundary",
        style_function=lambda _: {"color": "#f8c537", "weight": 3, "fillOpacity": 0.05},
    ).add_to(preview)
    folium.GeoJson(
        data=mapping(plan_data["inner_wgs"]),
        name="Working area",
        style_function=lambda _: {"color": "#00ff88", "weight": 2, "fillOpacity": 0.0, "dashArray": "6 5"},
    ).add_to(preview)

    for i, line in enumerate(plan_data["lines_wgs"], start=1):
        coords = [(float(lat), float(lon)) for lon, lat in list(line.coords)]
        folium.PolyLine(
            coords,
            color="#00e5ff" if i % 2 else "#39ff94",
            weight=3,
            opacity=0.95,
            tooltip=f"Pass {i}",
        ).add_to(preview)

    if plan_data["rows"]:
        first = plan_data["rows"][0]
        last = plan_data["rows"][-1]
        folium.Marker(
            location=[first["start_lat"], first["start_lon"]],
            tooltip="Route start",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(preview)
        folium.Marker(
            location=[last["end_lat"], last["end_lon"]],
            tooltip="Route end",
            icon=folium.Icon(color="red", icon="stop"),
        ).add_to(preview)

    folium.LayerControl(collapsed=True).add_to(preview)
    st_folium(preview, height=500, width=None, key="autosteer_plan_preview")

    rows_df = pd.DataFrame(plan_data["rows"])
    if rows_df.empty:
        st.warning("No valid passes found. Increase field size or reduce overlap/min pass length.")
    else:
        st.dataframe(rows_df, use_container_width=True, hide_index=True)

        csv_bytes = rows_df.to_csv(index=False).encode("utf-8")
        json_bytes = json.dumps(plan_data["rows"], indent=2).encode("utf-8")
        d1, d2, d3 = st.columns(3)
        d1.download_button("Download passes CSV", data=csv_bytes, file_name="autosteer_passes.csv", mime="text/csv")
        d2.download_button("Download passes JSON", data=json_bytes, file_name="autosteer_passes.json", mime="application/json")

        if d3.button("Save plan to history"):
            payload = {
                "plan_name": plan_data["plan_name"],
                "field": plan_data["field"],
                "boundary_mode": plan_data["boundary_mode"],
                "settings": plan_data["settings"],
                "summary": plan_data["summary"],
                "passes": plan_data["rows"],
                "generated_at": now_iso(),
            }
            saved = append_autosteer_plan(payload)

            event_field = plan_data["field"] if plan_data["boundary_mode"] == "Saved field" else "General"
            add_event(
                field_name=event_field,
                event_type="autosteer_plan",
                event_date=date.today().isoformat(),
                note=(
                    f"{plan_data['plan_name']} | passes {summary.get('pass_count', 0)} | "
                    f"route {summary.get('route_distance_km', 0)} km | ETA {summary.get('estimated_time_h', 0)} h"
                ),
                source="autosteer_assist",
                meta={"created_at": saved.get("created_at"), "field": plan_data["field"]},
            )
            st.success("Plan saved.")


st.subheader("4) Saved plans")
saved_plans = load_autosteer_plans()
if not saved_plans:
    st.info("No saved AutoSteer plans yet.")
else:
    hist_rows: List[Dict[str, Any]] = []
    for p in reversed(saved_plans[-30:]):
        summary = p.get("summary", {}) if isinstance(p, dict) else {}
        hist_rows.append(
            {
                "created_at": p.get("created_at", p.get("generated_at", "")),
                "plan_name": p.get("plan_name", ""),
                "field": p.get("field", ""),
                "mode": p.get("boundary_mode", ""),
                "passes": summary.get("pass_count", 0),
                "route_km": summary.get("route_distance_km", 0),
                "eta_h": summary.get("estimated_time_h", 0),
            }
        )
    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
    st.download_button(
        "Download saved plans JSON",
        data=json.dumps(saved_plans, indent=2).encode("utf-8"),
        file_name="autosteer_plans.json",
        mime="application/json",
    )
