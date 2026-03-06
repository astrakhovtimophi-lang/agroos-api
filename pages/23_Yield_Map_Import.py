import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from agro_utils import add_event, append_telematics, field_names_and_features
from styles import apply_styles

apply_styles()

st.title("🌾 Yield Map Import")
st.caption("Import yield maps from machinery/telematics CSV and analyze low/medium/high productivity zones.")

field_names, _ = field_names_and_features()
field_pick = st.selectbox("Field", ["General"] + field_names, index=0)

st.markdown("#### Upload CSV")
st.caption("Required columns: lat, lon, yield_t_ha. Optional: timestamp, machine, moisture_pct")
file = st.file_uploader("Yield map CSV", type=["csv"], key="yield_map_csv")

if file is not None:
    try:
        df = pd.read_csv(file)
    except Exception as e:
        st.error(f"CSV error: {e}")
        st.stop()

    required = {"lat", "lon", "yield_t_ha"}
    if not required.issubset(set(df.columns)):
        st.error(f"Missing columns: {sorted(required - set(df.columns))}")
        st.stop()

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["yield_t_ha"] = pd.to_numeric(df["yield_t_ha"], errors="coerce")
    df = df.dropna(subset=["lat", "lon", "yield_t_ha"])

    if df.empty:
        st.error("No valid points after parsing.")
        st.stop()

    q1 = float(df["yield_t_ha"].quantile(0.33))
    q2 = float(df["yield_t_ha"].quantile(0.66))

    def zone(v):
        if v <= q1:
            return "low"
        if v <= q2:
            return "medium"
        return "high"

    df["zone"] = df["yield_t_ha"].apply(zone)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Points", len(df))
    c2.metric("Mean yield", f"{df['yield_t_ha'].mean():.2f} t/ha")
    c3.metric("P10", f"{df['yield_t_ha'].quantile(0.1):.2f}")
    c4.metric("P90", f"{df['yield_t_ha'].quantile(0.9):.2f}")

    zdf = df.groupby("zone", as_index=False).agg(points=("zone", "size"), mean_yield=("yield_t_ha", "mean"))
    st.dataframe(zdf, use_container_width=True, hide_index=True)

    center_lat = float(df.iloc[0]["lat"])
    center_lon = float(df.iloc[0]["lon"])
    mp = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)

    colors = {"low": "#ff3b30", "medium": "#ffcc00", "high": "#00ff88"}
    for _, r in df.iterrows():
        folium.CircleMarker(
            location=[float(r["lat"]), float(r["lon"])],
            radius=3,
            color=colors.get(str(r["zone"]), "#00ccff"),
            fill=True,
            fill_opacity=0.8,
            tooltip=f"Yield: {float(r['yield_t_ha']):.2f} t/ha | zone: {r['zone']}",
        ).add_to(mp)

    st_folium(mp, height=460, width=None)

    st.subheader("Distribution")
    st.bar_chart(df["yield_t_ha"])

    # Save into telematics log to keep unified machine data history.
    sample_machine = str(df.get("machine", pd.Series(["unknown"])).iloc[0]) if "machine" in df.columns else "unknown"
    append_telematics(
        {
            "machine": sample_machine,
            "timestamp": str(df.get("timestamp", pd.Series([""])).iloc[0]) if "timestamp" in df.columns else "",
            "lat": center_lat,
            "lon": center_lon,
            "speed_kmh": 0.0,
            "fuel_lph": 0.0,
            "yield_points": int(len(df)),
            "yield_mean_t_ha": float(df["yield_t_ha"].mean()),
            "source": "yield_map_import",
        }
    )

    add_event(
        field_name=field_pick,
        event_type="yield_map_import",
        event_date=pd.Timestamp.now().date().isoformat(),
        note=f"Yield map imported: {len(df)} points, mean {df['yield_t_ha'].mean():.2f} t/ha",
        source="yield_map_page",
    )

    st.download_button(
        "Download classified yield points CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="yield_map_classified.csv",
        mime="text/csv",
    )

    st.success("Yield map processed and logged.")
else:
    st.info("Upload CSV to start yield map analysis.")
