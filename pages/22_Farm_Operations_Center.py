import math
from datetime import date, datetime
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from i18n import tr
from streamlit_folium import st_folium

from agro_utils import (
    add_event,
    append_compliance,
    append_crop_plan,
    append_machinery_log,
    append_operation,
    append_scouting,
    append_telematics,
    append_warehouse_transaction,
    field_names_and_features,
    load_compliance,
    load_crop_plan,
    load_machinery_logs,
    load_operations,
    load_pesticides_catalog,
    load_scouting,
    load_telematics,
    load_warehouse_transactions,
    now_iso,
    save_pesticides_catalog,
)
from styles import apply_styles

apply_styles()

st.title(tr("module_ops_center"))
st.caption("Unified workspace: crop plan, operations, machinery, telematics, warehouse, scouting and safety checks.")

field_names, field_feats = field_names_and_features()
field_choices = field_names if field_names else ["General"]


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


tabs = st.tabs(
    [
        "Overview",
        "Crop Plan",
        "Operations",
        "Machinery",
        "Warehouse",
        "Scouting",
        "Compliance",
    ]
)

with tabs[0]:
    st.subheader("Platform coverage")
    matrix = pd.DataFrame(
        [
            {"Feature": "Field map + boundaries", "Status": "Done"},
            {"Feature": "Satellite indices + composite", "Status": "Done"},
            {"Feature": "Scouting with geotag/photo", "Status": "Done"},
            {"Feature": "Operations planning", "Status": "Done"},
            {"Feature": "Machinery logs + telematics import", "Status": "Done"},
            {"Feature": "Warehouse transactions/stock", "Status": "Done"},
            {"Feature": "Pesticide compliance checks", "Status": "Done"},
            {"Feature": "Profitability and reports", "Status": "Done"},
            {"Feature": "AI agronomy assistant", "Status": "Done"},
            {"Feature": "Live GPS from hardware trackers", "Status": "CSV/API import ready"},
            {"Feature": "Native mobile offline app", "Status": "Web app only"},
        ]
    )
    st.dataframe(matrix, use_container_width=True, hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Crop plans", len(load_crop_plan()))
    c2.metric("Operations", len(load_operations()))
    c3.metric("Scouting records", len(load_scouting()))
    c4.metric("Compliance checks", len(load_compliance()))

with tabs[1]:
    st.subheader("Crop Plan & Rotation")
    with st.form("cp_add", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            season = st.text_input("Season", value=f"{date.today().year}")
        with a2:
            field_name = st.selectbox("Field", field_choices)
        with a3:
            crop = st.text_input("Crop", value="Wheat")

        b1, b2, b3 = st.columns(3)
        with b1:
            area_ha = st.number_input("Area (ha)", min_value=0.1, value=10.0, step=0.1)
        with b2:
            target_yield = st.number_input("Target yield (t/ha)", min_value=0.0, value=5.0, step=0.1)
        with b3:
            status = st.selectbox("Status", ["planned", "in_progress", "completed"], index=0)

        notes = st.text_area("Notes")
        ok = st.form_submit_button("Save crop plan")

    if ok:
        append_crop_plan(
            {
                "season": season.strip(),
                "field": field_name,
                "crop": crop.strip() or "Unknown",
                "area_ha": float(area_ha),
                "target_yield_t_ha": float(target_yield),
                "status": status,
                "notes": notes.strip(),
            }
        )
        add_event(
            field_name=field_name,
            event_type="crop_plan",
            event_date=date.today().isoformat(),
            note=f"Crop plan: {season} {crop}, {area_ha:.1f} ha, target {target_yield:.1f} t/ha",
            source="operations_center",
        )
        st.success("Crop plan saved.")

    cp = pd.DataFrame(load_crop_plan())
    if cp.empty:
        st.info("No crop plans yet.")
    else:
        st.dataframe(cp, use_container_width=True, hide_index=True)
        pivot = cp.pivot_table(index="field", columns="season", values="crop", aggfunc="last", fill_value="-")
        st.subheader("Rotation matrix")
        st.dataframe(pivot, use_container_width=True)

with tabs[2]:
    st.subheader("Operations Planner & Work Orders")
    with st.form("op_add", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            op_date = st.date_input("Operation date", value=date.today())
        with a2:
            field_name = st.selectbox("Field", field_choices, key="op_field")
        with a3:
            op_type = st.selectbox(
                "Operation",
                ["sowing", "fertilization", "spraying", "irrigation", "tillage", "harvest", "scouting"],
                index=0,
            )

        b1, b2, b3 = st.columns(3)
        with b1:
            product = st.text_input("Product/Input", value="")
        with b2:
            dose = st.text_input("Dose", value="")
        with b3:
            area_ha = st.number_input("Area covered (ha)", min_value=0.0, value=0.0, step=0.1)

        c1, c2, c3 = st.columns(3)
        with c1:
            machinery = st.text_input("Machinery", value="")
        with c2:
            operator = st.text_input("Operator", value="")
        with c3:
            status = st.selectbox("Status", ["planned", "in_progress", "done"], index=0)

        cost_uah = st.number_input("Operation cost (UAH)", min_value=0.0, value=0.0, step=100.0)
        note = st.text_area("Note")
        ok_op = st.form_submit_button("Save operation")

    if ok_op:
        append_operation(
            {
                "date": op_date.isoformat(),
                "field": field_name,
                "operation": op_type,
                "product": product.strip(),
                "dose": dose.strip(),
                "area_ha": float(area_ha),
                "machinery": machinery.strip(),
                "operator": operator.strip(),
                "status": status,
                "cost_uah": float(cost_uah),
                "note": note.strip(),
            }
        )
        add_event(
            field_name=field_name,
            event_type=f"operation_{op_type}",
            event_date=op_date.isoformat(),
            note=f"{op_type} | {product} {dose} | machine: {machinery} | operator: {operator}",
            cost=cost_uah,
            source="operations_center",
        )
        st.success("Operation saved.")

    ops = pd.DataFrame(load_operations())
    if ops.empty:
        st.info("No operations yet.")
    else:
        st.dataframe(ops.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

        grp = ops.groupby(["date", "status"], as_index=False).size().pivot(index="date", columns="status", values="size").fillna(0)
        if not grp.empty:
            st.subheader("Operations timeline")
            st.bar_chart(grp)

        st.download_button(
            "Download operations CSV",
            data=ops.to_csv(index=False).encode("utf-8"),
            file_name="operations_log.csv",
            mime="text/csv",
        )

with tabs[3]:
    st.subheader("Machinery & Telematics")
    with st.form("machine_add", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            m_date = st.date_input("Log date", value=date.today())
        with a2:
            machine_name = st.text_input("Machine")
        with a3:
            driver = st.text_input("Driver")

        b1, b2, b3 = st.columns(3)
        with b1:
            engine_hours = st.number_input("Engine hours", min_value=0.0, value=0.0, step=0.1)
        with b2:
            fuel_l = st.number_input("Fuel used (L)", min_value=0.0, value=0.0, step=1.0)
        with b3:
            worked_ha = st.number_input("Worked area (ha)", min_value=0.0, value=0.0, step=0.1)

        note = st.text_input("Note")
        ok_m = st.form_submit_button("Save machinery log")

    if ok_m and machine_name.strip():
        append_machinery_log(
            {
                "date": m_date.isoformat(),
                "machine": machine_name.strip(),
                "driver": driver.strip(),
                "engine_hours": float(engine_hours),
                "fuel_l": float(fuel_l),
                "worked_ha": float(worked_ha),
                "note": note.strip(),
            }
        )
        st.success("Machinery log saved.")

    st.markdown("#### Import telematics CSV")
    st.caption("Expected columns: machine,timestamp,lat,lon,speed_kmh,fuel_lph")
    csv = st.file_uploader("Telematics CSV", type=["csv"], key="telematics_csv")
    if csv is not None:
        try:
            df_t = pd.read_csv(csv)
            required = {"machine", "timestamp", "lat", "lon"}
            if not required.issubset(set(df_t.columns)):
                st.error(f"Missing columns: {sorted(required - set(df_t.columns))}")
            else:
                n_added = 0
                for _, r in df_t.iterrows():
                    append_telematics(
                        {
                            "machine": str(r.get("machine", "")).strip(),
                            "timestamp": str(r.get("timestamp", "")).strip(),
                            "lat": float(r.get("lat", 0.0)),
                            "lon": float(r.get("lon", 0.0)),
                            "speed_kmh": float(r.get("speed_kmh", 0.0)) if "speed_kmh" in df_t.columns else 0.0,
                            "fuel_lph": float(r.get("fuel_lph", 0.0)) if "fuel_lph" in df_t.columns else 0.0,
                        }
                    )
                    n_added += 1
                st.success(f"Imported telematics points: {n_added}")
        except Exception as e:
            st.error(f"CSV parse error: {e}")

    mlog = pd.DataFrame(load_machinery_logs())
    tlog = pd.DataFrame(load_telematics())

    if not mlog.empty:
        st.subheader("Machinery summary")
        ms = (
            mlog.groupby("machine", as_index=False)
            .agg(engine_hours=("engine_hours", "sum"), fuel_l=("fuel_l", "sum"), worked_ha=("worked_ha", "sum"))
            .sort_values("fuel_l", ascending=False)
        )
        ms["fuel_l_ha"] = ms.apply(lambda x: (x["fuel_l"] / x["worked_ha"]) if x["worked_ha"] > 0 else 0.0, axis=1)
        st.dataframe(ms, use_container_width=True, hide_index=True)

    if not tlog.empty:
        st.subheader("Telematics tracks")
        tlog["timestamp"] = pd.to_datetime(tlog["timestamp"], errors="coerce")
        tlog = tlog.dropna(subset=["timestamp", "lat", "lon"])
        machines = sorted(tlog["machine"].dropna().astype(str).unique().tolist())
        pick_m = st.selectbox("Machine track", machines)
        view = tlog[tlog["machine"].astype(str) == pick_m].sort_values("timestamp")

        # approximate distance
        dist = 0.0
        pts = view[["lat", "lon"]].to_numpy()
        for i in range(1, len(pts)):
            dist += haversine_km(float(pts[i - 1][0]), float(pts[i - 1][1]), float(pts[i][0]), float(pts[i][1]))

        c1, c2, c3 = st.columns(3)
        c1.metric("Points", len(view))
        c2.metric("Approx distance", f"{dist:.2f} km")
        c3.metric("Avg speed", f"{view['speed_kmh'].mean():.1f} km/h" if "speed_kmh" in view.columns else "n/a")

        center_lat = float(view.iloc[0]["lat"])
        center_lon = float(view.iloc[0]["lon"])
        mp = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)
        coords = view[["lat", "lon"]].to_numpy().tolist()
        folium.PolyLine(coords, color="#00ff88", weight=4, opacity=0.85).add_to(mp)
        folium.Marker(coords[0], tooltip="Start").add_to(mp)
        folium.Marker(coords[-1], tooltip="End").add_to(mp)
        st_folium(mp, height=420, width=None)

with tabs[4]:
    st.subheader("Warehouse & Inputs")
    with st.form("wh_tx", clear_on_submit=True):
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            tx_date = st.date_input("Date", value=date.today(), key="wh_date")
        with a2:
            direction = st.selectbox("Direction", ["IN", "OUT"], index=0)
        with a3:
            product = st.text_input("Product")
        with a4:
            unit = st.selectbox("Unit", ["L", "kg", "pcs", "ha-dose"], index=0)

        b1, b2, b3 = st.columns(3)
        with b1:
            qty = st.number_input("Quantity", min_value=0.0, value=0.0, step=1.0)
        with b2:
            unit_price = st.number_input("Unit price (UAH)", min_value=0.0, value=0.0, step=1.0)
        with b3:
            field_ref = st.selectbox("Field (for OUT)", ["General"] + field_choices)

        comment = st.text_input("Comment")
        ok_tx = st.form_submit_button("Save transaction")

    if ok_tx and product.strip() and qty > 0:
        signed_qty = qty if direction == "IN" else -qty
        append_warehouse_transaction(
            {
                "date": tx_date.isoformat(),
                "direction": direction,
                "product": product.strip(),
                "unit": unit,
                "qty": float(signed_qty),
                "unit_price_uah": float(unit_price),
                "field": field_ref,
                "comment": comment.strip(),
            }
        )
        if direction == "OUT":
            add_event(
                field_name=field_ref,
                event_type="input_consumption",
                event_date=tx_date.isoformat(),
                note=f"{product} {qty} {unit} used",
                cost=qty * unit_price,
                source="operations_center",
            )
        st.success("Warehouse transaction saved.")

    tx = pd.DataFrame(load_warehouse_transactions())
    if tx.empty:
        st.info("No warehouse transactions yet.")
    else:
        st.dataframe(tx.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

        stock = (
            tx.groupby(["product", "unit"], as_index=False)
            .agg(qty=("qty", "sum"), value_uah=("unit_price_uah", "mean"))
            .sort_values("qty", ascending=True)
        )
        stock["est_value_uah"] = stock["qty"] * stock["value_uah"]
        st.subheader("Current stock")
        st.dataframe(stock, use_container_width=True, hide_index=True)

        low_thr = st.number_input("Low stock threshold (abs qty)", min_value=0.0, value=20.0, step=1.0)
        low = stock[stock["qty"] <= low_thr]
        if not low.empty:
            st.warning("Low stock items detected")
            st.dataframe(low, use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("Scouting Tasks & Geotagged Notes")

    st.markdown("#### Pick location on map")
    base_map = folium.Map(location=[48.7, 33.7], zoom_start=6, control_scale=True)
    for feat in field_feats:
        props = feat.get("properties", {}) or {}
        name = props.get("name", "field")
        folium.GeoJson(
            feat,
            name=name,
            style_function=lambda _: {"color": "#00ff88", "weight": 2, "fillOpacity": 0.05},
            tooltip=name,
        ).add_to(base_map)

    map_res = st_folium(base_map, height=360, width=None, key="scouting_map")
    clicked = (map_res or {}).get("last_clicked") if isinstance(map_res, dict) else None
    default_lat = float(clicked.get("lat")) if isinstance(clicked, dict) else 48.7
    default_lon = float(clicked.get("lng")) if isinstance(clicked, dict) else 33.7

    with st.form("scouting_add", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            s_date = st.date_input("Date", value=date.today(), key="sc_date")
        with a2:
            s_field = st.selectbox("Field", ["General"] + field_choices, key="sc_field")
        with a3:
            severity = st.selectbox("Severity", ["low", "medium", "high"], index=1)

        b1, b2, b3 = st.columns(3)
        with b1:
            category = st.selectbox("Category", ["disease", "pest", "nutrition", "weed", "water", "other"], index=0)
        with b2:
            assignee = st.text_input("Assignee")
        with b3:
            due = st.date_input("Due date", value=date.today(), key="sc_due")

        c1, c2 = st.columns(2)
        with c1:
            lat_v = st.number_input("Latitude", value=default_lat, format="%.6f")
        with c2:
            lon_v = st.number_input("Longitude", value=default_lon, format="%.6f")

        note = st.text_area("Observation")
        photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"], key="sc_photo")
        ok_s = st.form_submit_button("Save scouting record")

    if ok_s and note.strip():
        photo_path = ""
        if photo is not None:
            photo_dir = Path("data") / "scouting_photos"
            photo_dir.mkdir(parents=True, exist_ok=True)
            fname = f"{int(datetime.now().timestamp())}_{photo.name}"
            save_path = photo_dir / fname
            save_path.write_bytes(photo.getvalue())
            photo_path = str(save_path)

        append_scouting(
            {
                "date": s_date.isoformat(),
                "field": s_field,
                "severity": severity,
                "category": category,
                "assignee": assignee.strip(),
                "due_date": due.isoformat(),
                "lat": float(lat_v),
                "lon": float(lon_v),
                "note": note.strip(),
                "photo_path": photo_path,
                "status": "open",
            }
        )
        add_event(
            field_name=s_field,
            event_type="scouting",
            event_date=s_date.isoformat(),
            note=f"{category} ({severity}) - {note[:120]}",
            source="operations_center",
        )
        st.success("Scouting record saved.")

    sc = pd.DataFrame(load_scouting())
    if sc.empty:
        st.info("No scouting records yet.")
    else:
        st.dataframe(sc.sort_values("date", ascending=False), use_container_width=True, hide_index=True)
        for _, row in sc.sort_values("date", ascending=False).head(5).iterrows():
            st.markdown(f"**{row.get('date')} | {row.get('field')} | {row.get('category')} ({row.get('severity')})**")
            st.write(row.get("note", ""))
            pp = row.get("photo_path", "")
            if pp and Path(pp).exists():
                st.image(pp, width=260)

with tabs[6]:
    st.subheader("Pesticide Compliance")

    catalog = load_pesticides_catalog()
    cat_df = pd.DataFrame(catalog)
    st.markdown("#### Product catalog")
    st.dataframe(cat_df, use_container_width=True, hide_index=True)

    with st.expander("Add product to catalog"):
        with st.form("cat_add", clear_on_submit=True):
            a1, a2, a3 = st.columns(3)
            with a1:
                p_name = st.text_input("Product")
            with a2:
                p_crop = st.text_input("Crop")
            with a3:
                p_active = st.text_input("Active")
            b1, b2, b3 = st.columns(3)
            with b1:
                max_dose = st.number_input("Max dose (L/ha)", min_value=0.0, value=0.0, step=0.1)
            with b2:
                rei_h = st.number_input("REI (hours)", min_value=0, value=24, step=1)
            with b3:
                phi_d = st.number_input("PHI (days)", min_value=0, value=30, step=1)
            ok_cat = st.form_submit_button("Add to catalog")
        if ok_cat and p_name.strip():
            catalog.append(
                {
                    "product": p_name.strip(),
                    "crop": p_crop.strip() or "Any",
                    "max_dose_l_ha": float(max_dose),
                    "rei_hours": int(rei_h),
                    "phi_days": int(phi_d),
                    "active": p_active.strip(),
                }
            )
            save_pesticides_catalog(catalog)
            st.success("Catalog updated.")
            st.rerun()

    st.markdown("#### Compliance check")
    with st.form("compliance_check", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            c_date = st.date_input("Application date", value=date.today(), key="cmp_date")
        with a2:
            c_field = st.selectbox("Field", ["General"] + field_choices, key="cmp_field")
        with a3:
            c_crop = st.text_input("Crop", value="Wheat")

        p_names = [r.get("product", "") for r in catalog]
        b1, b2, b3 = st.columns(3)
        with b1:
            c_product = st.selectbox("Product", p_names if p_names else [""], index=0)
        with b2:
            c_dose = st.number_input("Applied dose (L/ha)", min_value=0.0, value=0.0, step=0.1)
        with b3:
            c_worker_entry = st.date_input("Worker re-entry date", value=date.today(), key="cmp_re")

        harvest_date = st.date_input("Planned harvest date", value=date.today(), key="cmp_hv")
        note = st.text_input("Note")
        ok_cmp = st.form_submit_button("Run compliance check")

    if ok_cmp and c_product:
        ref = next((x for x in catalog if x.get("product") == c_product), None)
        if not ref:
            st.error("Product not found in catalog.")
        else:
            max_dose = float(ref.get("max_dose_l_ha", 0.0))
            rei_h = int(ref.get("rei_hours", 0))
            phi_d = int(ref.get("phi_days", 0))

            dose_ok = c_dose <= max_dose if max_dose > 0 else True
            re_hours = (datetime.combine(c_worker_entry, datetime.min.time()) - datetime.combine(c_date, datetime.min.time())).total_seconds() / 3600.0
            rei_ok = re_hours >= rei_h
            phi_days = (harvest_date - c_date).days
            phi_ok = phi_days >= phi_d

            status = "pass" if dose_ok and rei_ok and phi_ok else "warning"
            findings = []
            if not dose_ok:
                findings.append(f"Dose {c_dose} > label max {max_dose} L/ha")
            if not rei_ok:
                findings.append(f"REI violated: {re_hours:.1f}h < {rei_h}h")
            if not phi_ok:
                findings.append(f"PHI violated: {phi_days}d < {phi_d}d")
            if not findings:
                findings.append("All checked constraints passed.")

            record = {
                "application_date": c_date.isoformat(),
                "field": c_field,
                "crop": c_crop.strip(),
                "product": c_product,
                "dose_l_ha": float(c_dose),
                "label_max_l_ha": max_dose,
                "rei_hours_label": rei_h,
                "phi_days_label": phi_d,
                "worker_reentry": c_worker_entry.isoformat(),
                "planned_harvest": harvest_date.isoformat(),
                "status": status,
                "findings": findings,
                "note": note.strip(),
            }
            append_compliance(record)

            add_event(
                field_name=c_field,
                event_type="compliance_check",
                event_date=c_date.isoformat(),
                note=f"{c_product}: {status.upper()} | {'; '.join(findings)}",
                source="operations_center",
            )

            if status == "pass":
                st.success("Compliance PASS")
            else:
                st.warning("Compliance WARNING")
            for f in findings:
                st.write(f"- {f}")

    comp = pd.DataFrame(load_compliance())
    if not comp.empty:
        st.subheader("Compliance log")
        st.dataframe(comp.sort_values("application_date", ascending=False), use_container_width=True, hide_index=True)
        st.download_button(
            "Download compliance CSV",
            data=comp.to_csv(index=False).encode("utf-8"),
            file_name="compliance_log.csv",
            mime="text/csv",
        )

