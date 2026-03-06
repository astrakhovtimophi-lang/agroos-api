from datetime import date

import pandas as pd
import requests
import streamlit as st

from styles import apply_styles

apply_styles()

st.title("🌦 Weather + Field Conditions")
st.caption("Current weather, 14-day outlook, cumulative precipitation, GDD and operation windows.")

c1, c2, c3 = st.columns(3)
with c1:
    lat = st.number_input("Latitude", value=48.700000, format="%.6f", key="wx_lat")
with c2:
    lon = st.number_input("Longitude", value=33.700000, format="%.6f", key="wx_lon")
with c3:
    gdd_base = st.number_input("GDD base temperature (°C)", min_value=0.0, value=10.0, step=0.5)

if st.button("Update weather", key="wx_btn"):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": 14,
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"Weather error: {e}")
        st.stop()

    cur = data.get("current", {})
    st.subheader("Now")
    a, b, c, d = st.columns(4)
    a.metric("Temp (°C)", str(cur.get("temperature_2m", "—")))
    b.metric("Humidity (%)", str(cur.get("relative_humidity_2m", "—")))
    c.metric("Wind (m/s)", str(cur.get("wind_speed_10m", "—")))
    d.metric("Precip (mm)", str(cur.get("precipitation", "—")))

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    psum = daily.get("precipitation_sum", [])
    wmax = daily.get("wind_speed_10m_max", [])

    rows = []
    for i in range(len(dates)):
        t_hi = float(tmax[i]) if i < len(tmax) else None
        t_lo = float(tmin[i]) if i < len(tmin) else None
        rain = float(psum[i]) if i < len(psum) else None
        wind = float(wmax[i]) if i < len(wmax) else None

        gdd = None
        if t_hi is not None and t_lo is not None:
            gdd = max(((t_hi + t_lo) / 2.0) - gdd_base, 0.0)

        spray_ok = False
        if wind is not None and rain is not None:
            spray_ok = (wind <= 6.0) and (rain <= 1.0)

        rows.append(
            {
                "date": dates[i],
                "tmax": t_hi,
                "tmin": t_lo,
                "rain_mm": rain,
                "wind_max_m_s": wind,
                "gdd": gdd,
                "spray_window": "good" if spray_ok else "risk",
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        st.warning("No daily data returned.")
        st.stop()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date")

    df["rain_cum_mm"] = df["rain_mm"].fillna(0.0).cumsum()
    df["gdd_cum"] = df["gdd"].fillna(0.0).cumsum()

    st.subheader("14-day forecast")
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Rain total (14d)", f"{df['rain_mm'].fillna(0.0).sum():.1f} mm")
    c2.metric("Cumulative GDD (14d)", f"{df['gdd'].fillna(0.0).sum():.1f}")
    c3.metric("Good spray days", int((df["spray_window"] == "good").sum()))

    st.subheader("Cumulative rain and GDD")
    chart_df = df.set_index("date")[["rain_cum_mm", "gdd_cum"]]
    st.line_chart(chart_df)

    st.subheader("Operation windows")
    good = df[df["spray_window"] == "good"]["date"].dt.date.astype(str).tolist()
    risk = df[df["spray_window"] == "risk"]["date"].dt.date.astype(str).tolist()

    if good:
        st.success("Good spray windows: " + ", ".join(good[:8]))
    else:
        st.warning("No good spray windows in forecast.")

    if risk:
        st.info("Risk days (rain/wind): " + ", ".join(risk[:8]))

    st.download_button(
        "Download weather table CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="weather_14d_with_gdd.csv",
        mime="text/csv",
    )
