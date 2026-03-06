from datetime import date

import pandas as pd
import streamlit as st
from i18n import tr

from agro_utils import add_event, add_ndvi_record, field_names_and_features, load_ndvi_history
from styles import apply_styles

apply_styles()

st.title(tr("module_ndvi_trends"))
st.caption("Track NDVI over time and detect sudden drops.")

field_names, _ = field_names_and_features()
history = load_ndvi_history()
history_fields = sorted({str(r.get("field")) for r in history if r.get("field")})

all_fields = sorted(set(field_names + history_fields))
if not all_fields:
    all_fields = ["General"]

pick = st.selectbox("Field", all_fields, index=0)

with st.form("ndvi_manual_add", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        d = st.date_input("Date", value=date.today())
    with c2:
        ndvi_val = st.number_input("NDVI mean", min_value=-1.0, max_value=1.0, value=0.55, step=0.01, format="%.2f")
    source = st.selectbox("Source", ["manual", "zones_auto", "satellite_summary"], index=0)
    add = st.form_submit_button("Add NDVI record")

if add:
    add_ndvi_record(pick, d.isoformat(), ndvi_val, source=source)
    add_event(
        field_name=pick,
        event_type="ndvi_record",
        event_date=d.isoformat(),
        note=f"NDVI={ndvi_val:.3f} ({source})",
        source="ndvi_trends",
    )
    st.success("NDVI record added.")

hist_df = pd.DataFrame(load_ndvi_history())
if hist_df.empty:
    st.info("No NDVI history yet.")
    st.stop()

hist_df = hist_df[hist_df["field"].astype(str) == pick].copy()
if hist_df.empty:
    st.info("No NDVI data for selected field.")
    st.stop()

hist_df["date"] = pd.to_datetime(hist_df["date"], errors="coerce")
hist_df["ndvi_mean"] = pd.to_numeric(hist_df["ndvi_mean"], errors="coerce")
hist_df = hist_df.dropna(subset=["date", "ndvi_mean"]).sort_values("date")
if hist_df.empty:
    st.info("No valid NDVI rows.")
    st.stop()

st.subheader("NDVI chart")
st.line_chart(hist_df.set_index("date")["ndvi_mean"])

st.subheader("History")
st.dataframe(hist_df[["date", "ndvi_mean", "source", "created_at"]], use_container_width=True, hide_index=True)

if len(hist_df) >= 2:
    drop_thr = st.slider("Alert if NDVI drops by (%)", 5, 50, 12)

    latest = float(hist_df.iloc[-1]["ndvi_mean"])
    prev_window = hist_df.iloc[:-1].tail(3)
    prev_avg = float(prev_window["ndvi_mean"].mean())

    if prev_avg > 0:
        drop_pct = (prev_avg - latest) / prev_avg * 100.0
    else:
        drop_pct = 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Latest NDVI", f"{latest:.3f}")
    c2.metric("Prev avg (last 3)", f"{prev_avg:.3f}")
    c3.metric("Drop", f"{drop_pct:.1f}%")

    if drop_pct >= drop_thr:
        st.error(f"NDVI drop alert: {drop_pct:.1f}% (threshold {drop_thr}%)")
        if st.button("Save drop alert to timeline"):
            add_event(
                field_name=pick,
                event_type="ndvi_drop_alert",
                event_date=hist_df.iloc[-1]["date"].date().isoformat(),
                note=f"NDVI dropped by {drop_pct:.1f}% vs previous baseline.",
                source="ndvi_trends",
            )
            st.success("Alert saved to timeline.")
    else:
        st.success("No critical NDVI drop detected.")

st.download_button(
    "Download NDVI history CSV",
    data=hist_df.to_csv(index=False).encode("utf-8"),
    file_name=f"ndvi_history_{pick.replace(' ', '_')}.csv",
    mime="text/csv",
)
