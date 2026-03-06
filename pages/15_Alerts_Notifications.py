from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

from agro_utils import append_alert_log, load_alert_rules, load_tasks, now_iso, save_alert_rules
from styles import apply_styles

apply_styles()

st.title("🔔 Smart Alerts")
st.caption("Weather risk alerts + planner reminders.")

saved = load_alert_rules()

c1, c2 = st.columns(2)
with c1:
    lat = st.number_input("Latitude", value=float(saved.get("lat", 48.7)), format="%.6f")
with c2:
    lon = st.number_input("Longitude", value=float(saved.get("lon", 33.7)), format="%.6f")

c3, c4, c5 = st.columns(3)
with c3:
    frost_thr = st.number_input("Frost alert if min temp <=", value=float(saved.get("frost_thr", 2.0)), step=0.5)
with c4:
    rain_thr = st.number_input("Heavy rain alert if precipitation >=", value=float(saved.get("rain_thr", 15.0)), step=1.0)
with c5:
    wind_thr = st.number_input("Wind alert if max wind >=", value=float(saved.get("wind_thr", 12.0)), step=0.5)

reminder_days = st.slider("Task reminder for open tasks older than (days)", 1, 30, int(saved.get("reminder_days", 3)))

sv1, sv2 = st.columns(2)
with sv1:
    if st.button("Save alert profile"):
        save_alert_rules(
            {
                "lat": lat,
                "lon": lon,
                "frost_thr": frost_thr,
                "rain_thr": rain_thr,
                "wind_thr": wind_thr,
                "reminder_days": reminder_days,
                "updated_at": now_iso(),
            }
        )
        st.success("Alert profile saved.")

alerts = []

if sv2.button("Run alert checks"):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": 7,
        }
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        tmins = daily.get("temperature_2m_min", [])
        rains = daily.get("precipitation_sum", [])
        winds = daily.get("wind_speed_10m_max", [])

        for i, dt in enumerate(dates):
            tmin = float(tmins[i]) if i < len(tmins) else None
            rain = float(rains[i]) if i < len(rains) else None
            wind = float(winds[i]) if i < len(winds) else None

            if tmin is not None and tmin <= frost_thr:
                alerts.append(
                    {
                        "severity": "high",
                        "type": "frost",
                        "date": dt,
                        "message": f"Frost risk: min temp {tmin:.1f}°C (threshold {frost_thr:.1f}°C)",
                    }
                )
            if rain is not None and rain >= rain_thr:
                alerts.append(
                    {
                        "severity": "medium",
                        "type": "rain",
                        "date": dt,
                        "message": f"Heavy rain: {rain:.1f} mm (threshold {rain_thr:.1f} mm)",
                    }
                )
            if wind is not None and wind >= wind_thr:
                alerts.append(
                    {
                        "severity": "medium",
                        "type": "wind",
                        "date": dt,
                        "message": f"Strong wind: {wind:.1f} m/s (threshold {wind_thr:.1f} m/s)",
                    }
                )

    except Exception as e:
        st.error(f"Weather check failed: {e}")

    cutoff = datetime.now() - timedelta(days=reminder_days)
    for t in load_tasks():
        if bool(t.get("done")):
            continue
        created_raw = str(t.get("created") or "")
        title = str(t.get("task") or "").strip()
        if not title:
            continue

        try:
            created_dt = datetime.fromisoformat(created_raw)
        except Exception:
            continue

        if created_dt <= cutoff:
            age = (datetime.now() - created_dt).days
            alerts.append(
                {
                    "severity": "low",
                    "type": "task_reminder",
                    "date": datetime.now().date().isoformat(),
                    "message": f"Open task '{title}' is waiting for {age} days",
                }
            )

    append_alert_log(alerts)

if alerts:
    st.subheader(f"Alerts found: {len(alerts)}")
    df = pd.DataFrame(alerts)
    st.dataframe(df, use_container_width=True, hide_index=True)

    lines = [f"[{a['severity'].upper()}] {a['date']} - {a['message']}" for a in alerts]
    txt = "\n".join(lines)
    st.download_button(
        "Download alert digest (.txt)",
        data=txt.encode("utf-8"),
        file_name="alerts_digest.txt",
        mime="text/plain",
    )
else:
    st.info("Run alert checks to generate notifications.")
